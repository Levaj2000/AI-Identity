"""Tests for the OCSF API Activity mapping (audit_log → class_uid 6003).

Grounds the export against AI Identity's OCSF contributions: API Activity +
ai_operation profile (#1641), the attestation object in its final #1661 shape
(record_integrity profile, fingerprint hashes, required signatures), and
honest ``unmapped`` placement for producer facts with no native home.
"""

import base64
import datetime
import types

from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import ec

from common.ocsf import OCSF_VERSION, EntrySignature, audit_log_to_ocsf, select_chain

_ORG_HASH = "aa" * 32
_ORG_PREV = "bb" * 32
_GLOBAL_HASH = "cc" * 32
_GLOBAL_PREV = "dd" * 32


def _row(**overrides):
    base = dict(
        id=231,
        agent_id="a9c3e7d1-2b4f-4e6a-9c8d-3f5a7b1e2c4d",
        agent_name="ada",
        user_id="11111111-2222-4333-8444-555566667777",
        org_id="00000000-0000-0000-0000-000000000100",
        correlation_id="0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d",
        endpoint="/ada/tools/read_file",
        method="POST",
        decision="allow",
        cost_estimate_usd=None,
        latency_ms=90,
        request_metadata={"policy_version": 36},
        entry_hash=_GLOBAL_HASH,
        prev_hash=_GLOBAL_PREV,
        entry_hash_org=_ORG_HASH,
        prev_hash_org=_ORG_PREV,
        org_chain_seq=143,
        created_at=datetime.datetime(2026, 5, 4, 12, 0, 0, tzinfo=datetime.UTC),
    )
    base.update(overrides)
    return types.SimpleNamespace(**base)


class TestOcsfApiActivityMapping:
    def test_core_api_activity_fields(self):
        ev = audit_log_to_ocsf(_row())
        assert ev["class_uid"] == 6003  # API Activity
        assert ev["category_uid"] == 6  # Application Activity
        assert ev["activity_id"] == 1  # POST → Create
        assert ev["type_uid"] == 600301  # class_uid*100 + activity_id
        assert ev["metadata"]["profiles"] == ["ai_operation", "record_integrity"]
        assert ev["metadata"]["version"] == OCSF_VERSION
        assert ev["metadata"]["correlation_uid"] == "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"

    def test_record_integrity_profile_only_with_attestation(self):
        ev = audit_log_to_ocsf(_row(entry_hash_org=None, prev_hash_org=None, entry_hash=None))
        assert ev["metadata"]["profiles"] == ["ai_operation"]
        assert "attestation" not in ev

    def test_decision_maps_to_action_id(self):
        assert audit_log_to_ocsf(_row(decision="allow"))["action_id"] == 1
        assert audit_log_to_ocsf(_row(decision="allow"))["action"] == "Allowed"
        assert audit_log_to_ocsf(_row(decision="deny"))["action_id"] == 2
        assert audit_log_to_ocsf(_row(decision="error"))["action_id"] == 99

    def test_method_maps_to_activity_id(self):
        assert audit_log_to_ocsf(_row(method="GET"))["activity_id"] == 2
        assert audit_log_to_ocsf(_row(method="PATCH"))["activity_id"] == 3
        assert audit_log_to_ocsf(_row(method="DELETE"))["activity_id"] == 4
        # type_uid tracks activity_id
        assert audit_log_to_ocsf(_row(method="DELETE"))["type_uid"] == 600304

    def test_ai_agent_and_actor(self):
        ev = audit_log_to_ocsf(_row())
        assert ev["ai_agent"]["uid"] == "a9c3e7d1-2b4f-4e6a-9c8d-3f5a7b1e2c4d"
        assert ev["ai_agent"]["name"] == "ada"
        assert ev["actor"]["user"]["type_id"] == 1
        assert ev["http_request"]["http_method"] == "POST"
        assert ev["http_request"]["url"]["path"] == "/ada/tools/read_file"

    def test_attestation_prefers_org_chain(self):
        att = audit_log_to_ocsf(_row())["attestation"]
        assert att["uid"] == "231"
        # HMAC chain hashes are fingerprint objects: 99/Other + algorithm sibling,
        # NOT algorithm_id 3 (plain SHA-256) — the chain is keyed.
        assert att["entry_hash"] == {
            "algorithm_id": 99,
            "algorithm": "HMAC-SHA-256",
            "value": _ORG_HASH,
        }
        assert att["prev_entry_hash"]["value"] == _ORG_PREV
        assert att["chain_uid"] == "00000000-0000-0000-0000-000000000100"
        assert "signatures" not in att  # unsigned unless the export path signs

    def test_attestation_falls_back_to_global_chain(self):
        att = audit_log_to_ocsf(_row(entry_hash_org=None, prev_hash_org=None))["attestation"]
        assert att["entry_hash"]["value"] == _GLOBAL_HASH
        assert att["prev_entry_hash"]["value"] == _GLOBAL_PREV
        assert "chain_uid" not in att

    def test_genesis_sentinel_omits_prev_entry_hash(self):
        # The org chain's first row stores the literal "GENESIS" sentinel as
        # prev_hash_org. That's a missing predecessor, not a hash — the genesis
        # event must omit prev_entry_hash, never emit a fingerprint whose
        # value is "GENESIS".
        att = audit_log_to_ocsf(_row(prev_hash_org="GENESIS", org_chain_seq=1))["attestation"]
        assert att["entry_hash"]["value"] == _ORG_HASH
        assert "prev_entry_hash" not in att

    def test_genesis_sentinel_on_global_chain_also_omitted(self):
        att = audit_log_to_ocsf(_row(entry_hash_org=None, prev_hash_org=None, prev_hash="GENESIS"))[
            "attestation"
        ]
        assert att["entry_hash"]["value"] == _GLOBAL_HASH
        assert "prev_entry_hash" not in att

    def test_select_chain_matches_attestation(self):
        # The export signer uses select_chain; it must pick the same hash the
        # emitter displays, or the signature covers the wrong bytes.
        assert select_chain(_row()) == (
            _ORG_HASH,
            _ORG_PREV,
            "00000000-0000-0000-0000-000000000100",
        )
        assert select_chain(_row(entry_hash_org=None)) == (_GLOBAL_HASH, _GLOBAL_PREV, None)
        assert select_chain(_row(entry_hash_org=None, entry_hash=None)) == (None, None, None)
        # GENESIS sentinel → no predecessor, on either chain.
        assert select_chain(_row(prev_hash_org="GENESIS"))[1] is None
        assert select_chain(_row(entry_hash_org=None, prev_hash="GENESIS"))[1] is None

    def test_signed_event_carries_signature_and_verifies(self):
        key = ec.generate_private_key(ec.SECP256R1())
        row = _row()
        entry_hash = select_chain(row)[0]
        sig_der = key.sign(bytes.fromhex(entry_hash), ec.ECDSA(hashes.SHA256()))
        ev = audit_log_to_ocsf(
            row,
            EntrySignature(
                signature_b64=base64.b64encode(sig_der).decode("ascii"),
                key_id="local:testkey",
                signed_time_ms=1_780_000_000_000,
            ),
        )

        sigs = ev["attestation"]["signatures"]
        assert len(sigs) == 1
        assert sigs[0]["algorithm_id"] == 3  # ECDSA
        assert sigs[0]["algorithm"] == "ECDSA-P256-SHA256"
        assert sigs[0]["created_time"] == 1_780_000_000_000
        # digest restates the entry_hash fingerprint — what the signature covers
        assert sigs[0]["digest"] == ev["attestation"]["entry_hash"]

        # Signature bytes + key id have no digital_signature field — unmapped.
        assert ev["unmapped"]["signature_key_id"] == "local:testkey"
        recovered = base64.b64decode(ev["unmapped"]["signature_b64"])
        key.public_key().verify(recovered, bytes.fromhex(entry_hash), ec.ECDSA(hashes.SHA256()))

    def test_signature_ignored_without_chain(self):
        ev = audit_log_to_ocsf(
            _row(entry_hash_org=None, prev_hash_org=None, entry_hash=None),
            EntrySignature(signature_b64="ZmFrZQ==", key_id="local:x", signed_time_ms=0),
        )
        assert "attestation" not in ev
        assert "signature_b64" not in ev.get("unmapped", {})

    def test_latency_maps_to_duration(self):
        ev = audit_log_to_ocsf(_row())
        assert ev["duration"] == 90  # OCSF base duration (ms), not unmapped
        assert "latency_ms" not in ev["unmapped"]

    def test_unmapped_carries_homeless_producer_facts(self):
        um = audit_log_to_ocsf(_row())["unmapped"]
        assert um["policy_version"] == 36
        assert um["org_chain_seq"] == 143

    def test_severity_elevated_on_deny(self):
        assert audit_log_to_ocsf(_row(decision="allow"))["severity_id"] == 1
        assert audit_log_to_ocsf(_row(decision="deny"))["severity_id"] == 3

    def test_long_form_decisions_map(self):
        # Some writers / older rows store "allowed"/"denied" (not "allow"/"deny").
        assert audit_log_to_ocsf(_row(decision="allowed"))["action_id"] == 1
        assert audit_log_to_ocsf(_row(decision="denied"))["action_id"] == 2
        assert audit_log_to_ocsf(_row(decision=" Allowed "))["action_id"] == 1  # strip + case

    def test_unknown_decision_is_not_elevated(self):
        ev = audit_log_to_ocsf(_row(decision="weird"))
        assert ev["action_id"] == 0
        assert ev["action"] == "Unknown"
        assert ev["severity_id"] == 1  # don't alarm on vocabulary we didn't classify


class TestSignExportEntries:
    """The export-path signer: signs what select_chain picks, or degrades to {}."""

    def test_signs_each_entry_over_chain_hash(self, monkeypatch):
        from api.app.routers import audit as audit_router

        key = ec.generate_private_key(ec.SECP256R1())
        fake_signer = types.SimpleNamespace(
            sign=lambda msg: key.sign(msg, ec.ECDSA(hashes.SHA256())),
            key_id="local:testkey",
            backend="local",
        )
        monkeypatch.setattr(audit_router, "get_forensic_signer", lambda: fake_signer)

        rows = [_row(id=1), _row(id=2, entry_hash_org=None, prev_hash_org=None)]
        sigs = audit_router._sign_export_entries(rows)

        assert set(sigs) == {1, 2}
        # Row 1 signed over the org hash, row 2 over the global fallback —
        # the same selection the emitter displays.
        for row in rows:
            entry_hash = select_chain(row)[0]
            der = base64.b64decode(sigs[row.id].signature_b64)
            key.public_key().verify(der, bytes.fromhex(entry_hash), ec.ECDSA(hashes.SHA256()))
        assert sigs[1].key_id == "local:testkey"

    def test_unconfigured_signer_degrades_to_unsigned(self, monkeypatch):
        from api.app.routers import audit as audit_router
        from common.forensic.signer import ForensicSignerConfigError

        def _boom():
            raise ForensicSignerConfigError("no key configured")

        monkeypatch.setattr(audit_router, "get_forensic_signer", _boom)
        assert audit_router._sign_export_entries([_row()]) == {}

    def test_rows_without_chain_are_skipped(self, monkeypatch):
        from api.app.routers import audit as audit_router

        key = ec.generate_private_key(ec.SECP256R1())
        fake_signer = types.SimpleNamespace(
            sign=lambda msg: key.sign(msg, ec.ECDSA(hashes.SHA256())),
            key_id="local:testkey",
            backend="local",
        )
        monkeypatch.setattr(audit_router, "get_forensic_signer", lambda: fake_signer)

        rows = [_row(id=1, entry_hash_org=None, prev_hash_org=None, entry_hash=None)]
        assert audit_router._sign_export_entries(rows) == {}
