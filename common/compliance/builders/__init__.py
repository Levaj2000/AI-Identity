"""Per-profile bundle builders.

Each module here writes one profile's artifacts into a
``ComplianceExportBundle``. The shared bundle infra
(``common.compliance.bundle``) handles hashing, manifest construction,
and DSSE signing — profile builders only produce content.

Currently shipped:

- ``placeholder`` — emits a human-readable README explaining the
  profile is scoped but the builder is not yet implemented. Used by
  every profile until the real builder ships.

Planned:

- ``soc2`` — SOC 2 TSC 2017 (sprint 11)
- ``eu_ai_act`` — EU AI Act 2024 (sprint 11)
- ``nist_ai_rmf`` — NIST AI RMF 1.0 (sprint 11)
"""
