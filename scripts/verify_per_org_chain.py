"""Verify per-org HMAC chains after backfill (Phase 2 of per-org migration).

Read-only validator. Walks every org's chain in audit_log and checks:
  - All three per-org columns are populated (no NULL rows)
  - `org_chain_seq` is 1..N monotonic per org (no gaps, no duplicates)
  - `prev_hash_org` of row[i] equals `entry_hash_org` of row[i-1]
  - `entry_hash_org` recomputes to the stored value for every row

Outputs a JSON report on stdout. Exit code 0 if every org is valid.

This is the gate before flipping columns to NOT NULL in the follow-up
Alembic migration. Operator runs:
    python scripts/backfill_per_org_chain.py
    python scripts/verify_per_org_chain.py
    # if green:
    alembic upgrade head    # picks up the NOT NULL migration

Usage:
    DATABASE_URL=postgresql://... python scripts/verify_per_org_chain.py
    python scripts/verify_per_org_chain.py --org-id <uuid>
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import uuid
from dataclasses import asdict, dataclass, field
from typing import TYPE_CHECKING

# Make `common` importable when run directly.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from common.audit.writer import GENESIS, _ensure_utc, compute_entry_hash_org  # noqa: E402
from common.models import Organization  # noqa: E402
from common.models.audit_log import AuditLog  # noqa: E402
from common.models.base import SessionLocal  # noqa: E402

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


@dataclass
class OrgResult:
    org_id: str
    rows: int
    valid: bool
    first_broken_id: int | None = None
    reason: str | None = None


@dataclass
class Report:
    valid: bool
    total_orgs: int
    total_rows: int
    null_rows: int
    orgs: list[OrgResult] = field(default_factory=list)


def _resolve_hmac_key(db: Session, org_id: uuid.UUID) -> str | None:
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org and org.forensic_verify_key:
        return org.forensic_verify_key
    return None


def verify_org(db: Session, org_id: uuid.UUID) -> OrgResult:
    """Verify one org's chain end-to-end. Returns an OrgResult."""
    expected_prev = GENESIS
    expected_seq = 1
    hmac_key = _resolve_hmac_key(db, org_id)
    count = 0

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.org_id == org_id)
        .order_by(AuditLog.id.asc())
        .yield_per(1000)
    )

    for row in rows:
        count += 1

        if row.prev_hash_org is None or row.entry_hash_org is None or row.org_chain_seq is None:
            return OrgResult(
                org_id=str(org_id),
                rows=count,
                valid=False,
                first_broken_id=row.id,
                reason="per-org chain column is NULL",
            )

        if row.org_chain_seq != expected_seq:
            return OrgResult(
                org_id=str(org_id),
                rows=count,
                valid=False,
                first_broken_id=row.id,
                reason=f"seq gap: expected {expected_seq}, got {row.org_chain_seq}",
            )

        if row.prev_hash_org != expected_prev:
            return OrgResult(
                org_id=str(org_id),
                rows=count,
                valid=False,
                first_broken_id=row.id,
                reason=f"prev_hash_org mismatch at seq {row.org_chain_seq}",
            )

        recomputed = compute_entry_hash_org(
            agent_id=row.agent_id,
            endpoint=row.endpoint,
            method=row.method,
            decision=row.decision,
            cost_estimate_usd=(
                float(row.cost_estimate_usd) if row.cost_estimate_usd is not None else None
            ),
            latency_ms=row.latency_ms,
            request_metadata=row.request_metadata,
            created_at=_ensure_utc(row.created_at),
            prev_hash_org=row.prev_hash_org,
            hmac_key=hmac_key,
        )
        if recomputed != row.entry_hash_org:
            return OrgResult(
                org_id=str(org_id),
                rows=count,
                valid=False,
                first_broken_id=row.id,
                reason=f"entry_hash_org recompute mismatch at seq {row.org_chain_seq}",
            )

        expected_prev = row.entry_hash_org
        expected_seq += 1

    return OrgResult(org_id=str(org_id), rows=count, valid=True)


def run(*, org_id: uuid.UUID | None) -> int:
    db = SessionLocal()
    try:
        if org_id is not None:
            org_ids = [org_id]
        else:
            rows = db.execute(text("SELECT DISTINCT org_id FROM audit_log ORDER BY org_id")).all()
            org_ids = [r[0] if isinstance(r[0], uuid.UUID) else uuid.UUID(str(r[0])) for r in rows]

        null_count = db.execute(
            text(
                "SELECT COUNT(*) FROM audit_log "
                "WHERE prev_hash_org IS NULL "
                "OR entry_hash_org IS NULL "
                "OR org_chain_seq IS NULL"
            )
        ).scalar_one()

        results = [verify_org(db, oid) for oid in org_ids]
        report = Report(
            valid=all(r.valid for r in results) and null_count == 0,
            total_orgs=len(results),
            total_rows=sum(r.rows for r in results),
            null_rows=int(null_count),
            orgs=results,
        )
        print(json.dumps(asdict(report), indent=2, sort_keys=True))
        return 0 if report.valid else 1
    finally:
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Verify per-org audit chain")
    p.add_argument(
        "--org-id",
        type=lambda s: uuid.UUID(s),
        default=None,
        help="Verify only this org. Default: every org with rows.",
    )
    args = p.parse_args()
    sys.exit(run(org_id=args.org_id))


if __name__ == "__main__":
    main()
