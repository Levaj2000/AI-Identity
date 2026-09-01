"""Arrival-time verification for edge-ingested OCSF records.

Mirrors the cpex-ocsf-audit emitter's covered-bytes rule (its
``sign::signing_input``): strip ``fingerprint`` / ``signatures`` from
``attestation_list[0]`` and the two post-hash extras from ``unmapped``,
RFC 8785-canonicalize what remains, then

  * fingerprint  = SHA-256 hex of those bytes, and
  * signature    = ECDSA-P256-SHA256 (DER, base64 in
    ``unmapped.signature_b64``) over the DSSE PAE of those bytes.

Pure functions + an in-memory :class:`BatchVerifier`; all DB access stays
in the router so this module is unit-testable against raw records.
"""

from __future__ import annotations

import base64
import copy
import hashlib
from dataclasses import dataclass, field

import rfc8785
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

DSSE_PAYLOAD_TYPE = "application/vnd.ocsf.event+json"


def covered_bytes(event: dict) -> bytes:
    """Canonical bytes the emitter's fingerprint and signature commit to."""
    ev = copy.deepcopy(event)
    att_list = ev.get("attestation_list")
    if isinstance(att_list, list) and att_list and isinstance(att_list[0], dict):
        att_list[0].pop("fingerprint", None)
        att_list[0].pop("signatures", None)
    unmapped = ev.get("unmapped")
    if isinstance(unmapped, dict):
        unmapped.pop("signature_b64", None)
        unmapped.pop("signature_key_id", None)
        if not unmapped:
            ev.pop("unmapped", None)
    return rfc8785.dumps(ev)


def dsse_pae(payload: bytes) -> bytes:
    """DSSE Pre-Authentication Encoding over ``DSSE_PAYLOAD_TYPE``."""
    t = DSSE_PAYLOAD_TYPE.encode()
    return b"DSSEv1 %d %s %d %s" % (len(t), t, len(payload), payload)


def stream_stamps(event: dict) -> tuple[int | None, str | None, int | None, int | None]:
    """(epoch, stream_id, stream_seq, emission_seq) from unmapped."cpex.stream".

    The epoch is not decoration: the emitter documents stream_seq as dense
    within (epoch, stream_id), never across epochs — a producer restart
    opens a new epoch and legitimately resets the counter. Continuity
    checks that ignore the epoch flag every restart as a gap, which is a
    false alarm on the one event (a crash) the stream exists to survive.
    """
    stamps = event.get("unmapped", {})
    stamps = stamps.get("cpex.stream", {}) if isinstance(stamps, dict) else {}
    if not isinstance(stamps, dict):
        stamps = {}
    return (
        stamps.get("epoch"),
        stamps.get("stream_id"),
        stamps.get("stream_seq"),
        stamps.get("emission_seq"),
    )


def _epoch_regressed(record_epoch: int | None, tail_epoch: int | None) -> bool:
    """True when the record's epoch is strictly OLDER than the stream's.

    Epochs are producer boot times (Unix nanos), so they order. A record
    without an epoch after records that carried one (or vice versa) is not
    orderable — treated as not-a-regression rather than inventing one,
    since the equal-epoch density check above already covers the
    both-missing case.
    """
    return (
        isinstance(record_epoch, int) and isinstance(tail_epoch, int) and record_epoch < tail_epoch
    )


def dedupe_key_for(event: dict) -> str | None:
    """Idempotency identity: metadata.uid, else "<stream_id>#<stream_seq>"."""
    metadata = event.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("uid"), str) and metadata["uid"]:
        return metadata["uid"]
    _, stream_id, stream_seq, _ = stream_stamps(event)
    if stream_id is not None and stream_seq is not None:
        return f"{stream_id}#{stream_seq}"
    return None


@dataclass
class RecordCheck:
    """Verification outcome for one record.

    ``failures`` are integrity failures — the record itself cannot be
    trusted (bad signature, wrong fingerprint, wrong chain identity) —
    and quarantine it. ``anomalies`` are continuity observations on an
    otherwise crypto-valid record (a stream gap, a chain discontinuity):
    the record is stored verified with the anomaly on it, and the chain
    re-anchors here. One crashed edge epoch must not cascade-quarantine
    every record that follows it.
    """

    failures: list[str] = field(default_factory=list)
    anomalies: list[str] = field(default_factory=list)
    fingerprint: str | None = None
    metadata_uid: str | None = None
    chain_uid: str | None = None
    epoch: int | None = None
    stream_id: str | None = None
    stream_seq: int | None = None
    emission_seq: int | None = None
    chain_position: int | None = None

    @property
    def verified(self) -> bool:
        return not self.failures

    @property
    def dedupe_key(self) -> str | None:
        # Same identity rule as dedupe_key_for() — derived from the
        # fields check() extracted.
        if self.metadata_uid:
            return self.metadata_uid
        if self.stream_id is not None and self.stream_seq is not None:
            return f"{self.stream_id}#{self.stream_seq}"
        return None


class BatchVerifier:
    """Verifies a batch in arrival order, threading chain/stream state.

    ``chain_head`` is the last VERIFIED record's ``(metadata_uid,
    fingerprint)`` for the edge's chain (or None before genesis) —
    quarantined records never advance it, so one forged record doesn't
    let an attacker re-root the chain. ``stream_tails`` maps stream_id to
    the last VERIFIED stream_seq for the same reason: an unauthenticated
    record's stamps are claims, not state.
    """

    def __init__(
        self,
        public_key: ec.EllipticCurvePublicKey,
        *,
        expected_chain_uid: str,
        expected_key_id: str | None = None,
        chain_head: tuple[str | None, str] | None = None,
        chain_position: int = 0,
        stream_tails: dict[str, tuple[int | None, int]] | None = None,
        last_emission_seq: tuple[int | None, int] | None = None,
    ):
        self._key = public_key
        self._expected_chain_uid = expected_chain_uid
        self._expected_key_id = expected_key_id
        self._head = chain_head
        self._position = chain_position
        # stream_id -> (epoch, last verified stream_seq). The epoch scopes
        # the density check: a NEWER epoch is a producer restart and resets
        # the counter legitimately; only within one epoch is a non-dense
        # seq a gap. See stream_stamps() for why.
        self._tails = dict(stream_tails or {})
        # (epoch, last verified emission_seq) — emission_seq is the
        # producer process's global counter, so it resets with the epoch
        # for the same reason stream_seq does.
        self._last_emission = last_emission_seq

    def check(self, event: dict) -> RecordCheck:
        r = RecordCheck()

        metadata = event.get("metadata")
        if isinstance(metadata, dict) and isinstance(metadata.get("uid"), str):
            r.metadata_uid = metadata["uid"]
        r.epoch, r.stream_id, r.stream_seq, r.emission_seq = stream_stamps(event)

        att = self._attestation(event, r)
        self._verify_crypto(event, att, r)
        if not r.verified:
            # An untrustworthy record's stamps are unauthenticated claims:
            # it consumes no chain position and moves no stream state.
            return r

        self._check_chain(att, r)
        self._check_streams(r)
        self._position += 1
        r.chain_position = self._position
        self._head = (r.metadata_uid, r.fingerprint)
        return r

    # ── pieces ──────────────────────────────────────────────────────

    def _attestation(self, event: dict, r: RecordCheck) -> dict | None:
        att_list = event.get("attestation_list")
        if not (isinstance(att_list, list) and att_list and isinstance(att_list[0], dict)):
            r.failures.append("unsigned record — no attestation_list")
            return None
        att = att_list[0]
        r.chain_uid = att.get("chain_uid")
        if r.chain_uid != self._expected_chain_uid:
            r.failures.append(
                f"chain_uid mismatch: record claims {r.chain_uid!r}, "
                f"edge is registered for {self._expected_chain_uid!r}"
            )
        return att

    def _verify_crypto(self, event: dict, att: dict | None, r: RecordCheck) -> None:
        try:
            cb = covered_bytes(event)
        except (TypeError, ValueError) as exc:
            r.failures.append(f"record is not canonicalizable: {exc}")
            return
        r.fingerprint = hashlib.sha256(cb).hexdigest()

        if att is not None:
            claimed = att.get("fingerprint")
            claimed = claimed.get("value") if isinstance(claimed, dict) else None
            if not isinstance(claimed, str):
                r.failures.append("missing fingerprint value")
            elif claimed.lower() != r.fingerprint:
                r.failures.append(
                    f"fingerprint mismatch: computed {r.fingerprint[:16]}…, claimed {claimed[:16]}…"
                )

        unmapped = event.get("unmapped")
        unmapped = unmapped if isinstance(unmapped, dict) else {}
        sig_b64 = unmapped.get("signature_b64")
        if not isinstance(sig_b64, str) or not sig_b64:
            r.failures.append("no signature — unmapped.signature_b64 absent")
            return
        key_id = unmapped.get("signature_key_id")
        if self._expected_key_id is not None and key_id != self._expected_key_id:
            r.failures.append(
                f"signature_key_id mismatch: record claims {key_id!r}, "
                f"edge registered {self._expected_key_id!r}"
            )
        try:
            sig = base64.b64decode(sig_b64, validate=True)
        except Exception:
            r.failures.append("invalid base64 in signature_b64")
            return
        try:
            self._key.verify(sig, dsse_pae(cb), ec.ECDSA(hashes.SHA256()))
        except InvalidSignature:
            r.failures.append("signature verification failed")

    def _check_chain(self, att: dict | None, r: RecordCheck) -> None:
        if att is None:
            return
        prev = att.get("prev_event")
        if self._head is None:
            if prev is not None:
                r.anomalies.append(
                    "chain re-anchored: prev_event present but chain has no verified head"
                )
            return
        head_uid, head_fp = self._head
        if not isinstance(prev, dict):
            r.anomalies.append(f"chain re-anchored: missing prev_event — head was {head_uid!r}")
            return
        prev_fp = prev.get("fingerprint")
        prev_fp = prev_fp.get("value") if isinstance(prev_fp, dict) else prev_fp
        if prev.get("uid") != head_uid:
            r.anomalies.append(
                f"chain discontinuity: prev_event.uid {prev.get('uid')!r} "
                f"does not match chain head {head_uid!r} — re-anchored"
            )
        elif not isinstance(prev_fp, str) or prev_fp.lower() != head_fp:
            r.anomalies.append(
                "chain discontinuity: prev_event fingerprint does not match head — re-anchored"
            )

    def _check_streams(self, r: RecordCheck) -> None:
        # Density is a per-(epoch, stream_id) property. Within one epoch a
        # non-dense seq means records were lost — an anomaly. A NEWER epoch
        # is a restart: the producer's boot-time epoch grew, the counters
        # reset, and flagging that as a gap would cry wolf on the one event
        # (a crash) the stream is designed to survive. An OLDER epoch is
        # wrong in the other direction — epochs are boot-ordered, so going
        # backwards means late replay of a dead process or clock trouble,
        # and that IS worth a look.
        if r.stream_id is not None and isinstance(r.stream_seq, int):
            tail = self._tails.get(r.stream_id)
            if tail is not None:
                tail_epoch, tail_seq = tail
                if r.epoch == tail_epoch:
                    if r.stream_seq != tail_seq + 1:
                        r.anomalies.append(
                            f"stream_seq gap in {r.stream_id}: "
                            f"expected {tail_seq + 1}, got {r.stream_seq}"
                        )
                elif _epoch_regressed(r.epoch, tail_epoch):
                    r.anomalies.append(
                        f"epoch regression in {r.stream_id}: {r.epoch} after {tail_epoch}"
                    )
                # else: newer epoch — a restart; density restarts with it.
            self._tails[r.stream_id] = (r.epoch, r.stream_seq)
        if isinstance(r.emission_seq, int):
            if self._last_emission is not None:
                last_epoch, last_seq = self._last_emission
                if r.epoch == last_epoch and r.emission_seq <= last_seq:
                    r.anomalies.append(
                        f"emission_seq not monotonic: {r.emission_seq} after {last_seq}"
                    )
                # A different epoch resets emission_seq with the process;
                # regression across epochs is already reported once above.
            self._last_emission = (r.epoch, r.emission_seq)
