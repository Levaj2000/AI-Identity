"""Deterministic hash of an export's ``agent_ids`` scope.

Drives the idempotency unique index on ``compliance_exports``. Postgres
can't unique-index an ARRAY in a way that treats ``[a,b]`` and
``[b,a]`` as equal, so we precompute a canonical hash at write time.

Contract:
- ``None`` or empty list → empty string (whole-org sentinel, distinct
  from any real id set).
- Non-empty list → SHA-256 hex of the sorted, dash-form UUIDs joined
  by ``\\n``. The joiner is newline (not comma) so a pathological id
  with a comma in it couldn't collide with a different list — UUIDs
  never contain newlines.
"""

from __future__ import annotations

import hashlib
import uuid  # noqa: TC003 — used at runtime via str(aid)


def agent_ids_hash(agent_ids: list[uuid.UUID] | None) -> str:
    """Canonical hash for the idempotency unique index.

    Returns the empty string for ``None`` / ``[]`` so the unique-index
    bucket for "whole org" is distinct from any real id set. Non-empty
    lists are sorted by their canonical UUID string form before
    hashing, so ``[A, B]`` and ``[B, A]`` collapse to the same value.
    """
    if not agent_ids:
        return ""
    normalized = sorted(str(aid) for aid in agent_ids)
    joined = "\n".join(normalized).encode("utf-8")
    return hashlib.sha256(joined).hexdigest()
