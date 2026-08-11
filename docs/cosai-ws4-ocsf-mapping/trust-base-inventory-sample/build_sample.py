#!/usr/bin/env python3
"""Build (and verify) the agent trust-base inventory sample for ocsf-schema#1724.

Three chained Discovery-style events showing the class proposed in
https://github.com/ocsf/ocsf-schema/issues/1724 — an agent trust-base
inventory snapshot (declared configuration + executed parameters) with the
merged ``record_integrity`` profile (#1661, OCSF 1.9) applied per emission.

Design constraints, in the spirit of the other samples in this tree:

- **Stdlib only.** Every fingerprint here is unkeyed SHA-256, so anyone can
  recompute the whole chain with nothing but python3 — no keys, no secrets,
  no third-party packages. (The signed variant — per-event ECDSA over the
  fingerprint — is demonstrated by the production export in
  ``../ocsf-log-reference-bundle/``; this sample deliberately exercises the
  ``at_least_one(fingerprint, signatures)`` constraint via fingerprint alone.)
- **Every digest has a named preimage.** Content digests (tool schemas,
  policy bundles, adapters, charter) are SHA-256 over the ASCII preimages in
  ``DIGEST_PREIMAGES`` below, so the sample is recomputable end to end —
  nothing is hand-typed hex.
- **Event fingerprints follow the merged #1661 semantics** (as also
  implemented in ``integrations/cpex-ocsf-audit`` v0.0.3): the whole event is
  hashed with the attestation's own ``uid`` / ``chain_uid`` /
  ``authority_uid`` / ``prev_event`` inside the hashed bytes; only
  ``fingerprint`` and ``signatures`` are excluded. Serialization is
  sorted-keys compact JSON (UTF-8) — declared honestly as
  ``serialization_id`` 99 with the sibling naming it, not claimed as JCS.

Placeholder UIDs: the proposed class does not exist in any released schema,
so ``class_uid`` uses a vendor-namespace placeholder (1000000+ range, per
OCSF convention) and ``metadata.version`` says ``1.10.0-dev``. Final
numbering, naming, and requirement levels are entirely the working group's.

Usage:
    python3 build_sample.py            # regenerate the .ndjson next to this file
    python3 build_sample.py --verify   # recompute digests + chain from the committed file
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import sys
from pathlib import Path

OUT = Path(__file__).resolve().parent / "agent-trust-base-inventory.sample.ndjson"

# ---------------------------------------------------------------------------
# Identities — same demo org / agent as the production reference bundle, so
# these Discovery events read as companions to that bundle's API Activity
# chain ("what the agent did" there; "what the agent *was*" here).
# ---------------------------------------------------------------------------
ORG_UID = "f3576cf6-87ff-4c07-b446-e6ac526236a5"
AGENT_UID = "32928870-56a1-4518-be76-7e99bfcdeac4"
AGENT_NAME = "QA-eae97318"
INSTANCE_UID = "0c9b8f2e-5a41-4d7f-9e2a-6b3c1d8e4f70"  # this run of the agent
CORRELATION_UID = "corr-4e1f9a72"
AUTHORITY_UID = (
    "gateway.ai-identity.co"  # the attesting authority (#1661 attestation.authority_uid)
)

# Vendor-namespace placeholder for the proposed class (Discovery, category 5).
CLASS_UID = 1000005
CATEGORY_UID = 5
OCSF_VERSION = "1.10.0-dev"  # proposal targets v1.10.0; nothing released carries this class

# 2026-08-11T09:00:00Z and two mid-session re-emissions.
T_BASELINE = 1786438800000
T_TOOL_REFRESH = T_BASELINE + 300_000  # +5 min
T_ADAPTER_LOAD = T_BASELINE + 540_000  # +9 min

# Content digests: SHA-256 over these ASCII preimages. In a real producer the
# preimage is the artifact bytes (tools/list response, policy bundle, adapter
# safetensors, charter document); here each preimage *names* what would be
# hashed so the sample stays recomputable without shipping artifacts.
DIGEST_PREIMAGES = {
    "tool_schema_v41": "mcp://mcp.ai-identity.internal/billing-tools tools/list revision v41",
    "tool_schema_v42": "mcp://mcp.ai-identity.internal/billing-tools tools/list revision v42 (+billing.refund_execute)",
    "policy_v10": "org-gateway-policy bundle version 10",
    "charter_v3": "agent charter document revision 3",
    "adapter_registry": "refunds-tone-lora 1.4.0 artifact as published in the adapter registry",
    "adapter_loaded": "refunds-tone-lora 1.4.0 artifact bytes actually mapped at load time (does NOT match registry)",
}

EVENT_FP_SERIALIZATION = (
    "sorted-keys compact JSON (UTF-8); attestation fingerprint/signatures excluded"
)


def sha256_hex(preimage: str) -> str:
    return hashlib.sha256(preimage.encode("utf-8")).hexdigest()


def content_fp(preimage_key: str) -> dict:
    """A fingerprint object for a content digest (plain SHA-256, hex)."""
    return {
        "algorithm_id": 3,
        "algorithm": "SHA-256",
        "encoding_id": 1,  # Hex
        "value": sha256_hex(DIGEST_PREIMAGES[preimage_key]),
    }


def canonical(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":")).encode("utf-8")


def event_fingerprint_value(event: dict) -> str:
    """SHA-256 over the event with attestation fingerprint/signatures excluded.

    Merged #1661 semantics: ``uid`` / ``chain_uid`` / ``authority_uid`` /
    ``prev_event`` stay *inside* the hashed bytes, so neither the claimed
    authority nor the chain linkage can be swapped after the fact.
    """
    stripped = copy.deepcopy(event)
    for att in stripped.get("attestation_list", []):
        att.pop("fingerprint", None)
        att.pop("signatures", None)
    return hashlib.sha256(canonical(stripped)).hexdigest()


def event_fp_object(value: str) -> dict:
    return {
        "algorithm_id": 3,
        "algorithm": "SHA-256",
        "encoding_id": 1,
        "serialization_id": 99,
        "serialization": EVENT_FP_SERIALIZATION,
        "value": value,
    }


def ai_agent_object() -> dict:
    # Merged ai_agent object (uid / instance_uid / version / charter /
    # ai_model verified against ocsf-schema main) — the identity spine the
    # proposed class inherits rather than reinvents. ``charter`` is a ``file``
    # object in the dictionary, so the charter's content digest rides its
    # ``hashes`` array natively — no new attribute needed.
    return {
        "uid": AGENT_UID,
        "instance_uid": INSTANCE_UID,
        "name": AGENT_NAME,
        "version": "2026.08.01",
        "type_id": 1,
        "type": "Native",
        "ai_model": {
            "ai_provider": "Anthropic",
            "name": "claude-sonnet-5",
            "version": "2026-06-15",
        },
        "charter": {
            "name": "agent-charter-r3.md",
            "hashes": [content_fp("charter_v3")],
        },
    }


def base_event(uid: str, time_ms: int, activity_id: int, activity_name: str) -> dict:
    return {
        "activity_id": activity_id,
        "activity_name": activity_name,
        "category_uid": CATEGORY_UID,
        "class_uid": CLASS_UID,
        "type_uid": CLASS_UID * 100 + activity_id,
        "severity_id": 1,
        "time": time_ms,
        "metadata": {
            "uid": uid,
            "version": OCSF_VERSION,
            "profiles": ["record_integrity"],
            "correlation_uid": CORRELATION_UID,
        },
        "ai_agent": ai_agent_object(),
    }


def artifact(name: str, type_id: int, type_name: str, preimage_key: str, **extra: str) -> dict:
    """An ``agent_artifact`` (class-draft shape): typed, digest-anchored."""
    entry: dict = {"name": name, **extra, "type_id": type_id, "type": type_name}
    entry["fingerprint"] = content_fp(preimage_key)
    return entry


def declared_configuration(tool_schema_key: str, adapters: list[dict]) -> dict:
    """The trust base as *declared*: registry/manifest view, digest-anchored.

    Shape per the class draft (docs/ocsf-1724-class-draft/): one typed
    ``artifacts`` array rather than per-kind arrays — the ``type_id`` enum
    says what each element is. The charter is NOT here: its digest rides
    ``ai_agent.charter.hashes`` (existing ``file`` object), per the draft.
    """
    return {
        # Hosted-model nuance: no local artifact to digest, so the pinned
        # (provider, name, version) tuple IS the trust-base element. Digests
        # apply to locally loaded artifacts (adapters, schemas, policies).
        "ai_model": {
            "ai_provider": "Anthropic",
            "name": "claude-sonnet-5",
            "version": "2026-06-15",
        },
        "artifacts": [
            artifact(
                "billing-tools",
                3,
                "Tool Schema",
                tool_schema_key,
                uid="mcp://mcp.ai-identity.internal/billing-tools",
            ),
            artifact("org-gateway-policy", 4, "Policy Bundle", "policy_v10", version="10"),
            *adapters,
        ],
    }


def executed_parameters(tools_invoked: list[str], adapters_loaded: list[dict]) -> dict:
    """The trust base as *enforced/observed* in the executing process.

    Credentials are references + scopes only — never material. ``mandate``
    ties to the delegation grant the agent acts under (the Mandate Service
    shape from AI-IDENTITY-AGENTIC-IAM-EXAMPLES.md).
    """
    executed = {
        "tool_allowlist": ["billing.get_invoice", "billing.refund_status", "kb.search"],
        "sampling": {"temperature": 0.2, "top_p": 0.95, "max_output_tokens": 2048},
        "tools_invoked": tools_invoked,
        "credentials": [
            {
                "type_id": 4,
                "type": "Delegation Grant",
                "uid": "mnd_a1b2c3d4",
                "scopes": ["read:billing"],
            },
            {
                "type_id": 1,
                "type": "API Key",
                "uid": "key_7f3e2d1c",
                "scopes": ["gateway:invoke"],
            },
        ],
    }
    if adapters_loaded:
        # Artifacts actually loaded, digests over the bytes as mapped — the
        # counterpart consumers compare against declared_configuration.artifacts.
        executed["artifacts"] = adapters_loaded
    return executed


def build_events() -> list[dict]:
    events: list[dict] = []
    prev: dict | None = None  # {"uid": ..., "type_uid": ..., "fingerprint": {...}}

    # ---- Event 1: session-start baseline (activity 2, Collect) -------------
    ev1 = base_event("tbi-0001", T_BASELINE, 2, "Collect")
    ev1["declared_configuration"] = declared_configuration("tool_schema_v41", adapters=[])
    ev1["executed_parameters"] = executed_parameters(tools_invoked=[], adapters_loaded=[])

    # ---- Event 2: mid-session tool-schema refresh (activity 3, proposed
    # "Change") — the MCP source re-served tools/list with a new digest
    # (adds billing.refund_execute). Emitted BEFORE any refreshed tool
    # serves a call (admission control, not forensics). Note the executed
    # allowlist does NOT pick up the new tool: policy hasn't admitted it —
    # declared/executed divergence a consumer computes from this one event.
    ev2 = base_event("tbi-0002", T_TOOL_REFRESH, 3, "Change")
    ev2["declared_configuration"] = declared_configuration("tool_schema_v42", adapters=[])
    ev2["executed_parameters"] = executed_parameters(
        tools_invoked=["kb.search", "billing.get_invoice"], adapters_loaded=[]
    )

    # ---- Event 3: adapter initialization mid-task (activity 3) — the
    # registry-declared digest and the digest of the bytes actually mapped
    # DISAGREE (the Sleeper-Agents scenario: artifact swapped between
    # registry and load). The producer reports both sides without judging;
    # the mismatch is computable downstream — and because this emission
    # precedes the adapter's first inference, a subscribed PDP can deny
    # before the artifact executes.
    ev3 = base_event("tbi-0003", T_ADAPTER_LOAD, 3, "Change")
    ev3["declared_configuration"] = declared_configuration(
        "tool_schema_v42",
        adapters=[artifact("refunds-tone-lora", 2, "Adapter", "adapter_registry", version="1.4.0")],
    )
    ev3["executed_parameters"] = executed_parameters(
        tools_invoked=["kb.search", "billing.get_invoice", "billing.refund_status"],
        adapters_loaded=[
            artifact("refunds-tone-lora", 2, "Adapter", "adapter_loaded", version="1.4.0")
        ],
    )

    for ev in (ev1, ev2, ev3):
        attestation: dict = {
            "uid": ev["metadata"]["uid"],
            "chain_uid": INSTANCE_UID,  # chain scoped to the agent *instance*
            "authority_uid": AUTHORITY_UID,
        }
        if prev is not None:
            attestation["prev_event"] = prev
        ev["attestation_list"] = [attestation]
        fp_value = event_fingerprint_value(ev)
        attestation["fingerprint"] = event_fp_object(fp_value)
        prev = {
            "uid": ev["metadata"]["uid"],
            "type_uid": ev["type_uid"],
            "fingerprint": event_fp_object(fp_value),
        }
        events.append(ev)

    return events


def write(events: list[dict]) -> None:
    with OUT.open("w", encoding="utf-8") as fh:
        for ev in events:
            fh.write(json.dumps(ev, separators=(", ", ": ")) + "\n")
    print(f"wrote {len(events)} events -> {OUT.name}")


def verify() -> int:
    lines = OUT.read_text(encoding="utf-8").splitlines()
    events = [json.loads(line) for line in lines if line.strip()]
    ok = True

    known_digests = {sha256_hex(p) for p in DIGEST_PREIMAGES.values()}
    prev_fp: str | None = None
    prev_uid: str | None = None
    for idx, ev in enumerate(events, start=1):
        att = ev["attestation_list"][0]
        # 1. Event fingerprint recomputes.
        recomputed = event_fingerprint_value(ev)
        if recomputed != att["fingerprint"]["value"]:
            print(f"✗ event {idx}: fingerprint mismatch")
            ok = False
        # 2. Chain linkage: prev_event carries the predecessor's fingerprint + uid.
        pe = att.get("prev_event")
        if idx == 1:
            if pe is not None:
                print("✗ event 1: genesis must omit prev_event")
                ok = False
        else:
            if pe is None or pe["fingerprint"]["value"] != prev_fp or pe["uid"] != prev_uid:
                print(f"✗ event {idx}: chain linkage broken")
                ok = False
        # 3. Every content digest resolves to a named preimage.
        for fp_holder in _iter_content_fingerprints(ev):
            if fp_holder["value"] not in known_digests:
                print(f"✗ event {idx}: unknown content digest {fp_holder['value'][:16]}…")
                ok = False
        prev_fp = att["fingerprint"]["value"]
        prev_uid = att["uid"]

    # 4. The divergence the sample exists to show: event 3's declared adapter
    # digest (type_id 2) differs from the loaded-bytes digest.
    ev3 = events[-1]

    def adapter_digest(section: str) -> str:
        entries = [a for a in ev3[section]["artifacts"] if a.get("type_id") == 2]
        return entries[0]["fingerprint"]["value"]

    if adapter_digest("declared_configuration") == adapter_digest("executed_parameters"):
        print("✗ event 3: expected declared/loaded adapter digest divergence")
        ok = False

    if ok:
        print(
            f"✓ {len(events)} events: fingerprints recompute, chain links, "
            "content digests resolve to named preimages, "
            "event-3 declared≠loaded divergence present"
        )
    return 0 if ok else 1


def _iter_content_fingerprints(ev: dict):
    """Yield every content fingerprint in declared/executed/ai_agent sections.

    Covers both carriers: ``fingerprint`` (agent_artifact) and ``hashes[]``
    (the charter's ``file`` object on ``ai_agent``).
    """

    def walk(node):
        if isinstance(node, dict):
            fp = node.get("fingerprint")
            if isinstance(fp, dict) and "value" in fp:
                yield fp
            for h in node.get("hashes") or []:
                if isinstance(h, dict) and "value" in h:
                    yield h
            for v in node.values():
                yield from walk(v)
        elif isinstance(node, list):
            for item in node:
                yield from walk(item)

    for section in ("declared_configuration", "executed_parameters", "ai_agent"):
        yield from walk(ev.get(section, {}))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--verify", action="store_true", help="verify the committed ndjson")
    args = parser.parse_args()
    if args.verify:
        return verify()
    write(build_events())
    return verify()


if __name__ == "__main__":
    sys.exit(main())
