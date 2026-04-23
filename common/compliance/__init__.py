"""Compliance export builder — infrastructure shared by all profiles.

Submodules:

- ``agent_ids_hash`` — deterministic hash for the idempotency guard
- ``manifest`` — canonical manifest bytes + DSSE envelope (new payloadType)
- ``bundle`` — streaming ZIP writer + per-file SHA-256 accounting
- ``job`` — FSM transitions (queued → building → ready|failed)
- ``builder`` — orchestrator that runs a job through the build pipeline
- ``builders.placeholder`` — placeholder profile emits a TODO manifest

Profile-specific builders (SOC 2, EU AI Act, NIST AI RMF) layer on top
of ``bundle`` + ``manifest`` and are added in follow-on sprint items.
"""
