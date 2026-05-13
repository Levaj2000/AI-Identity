"""Backfill per-org HMAC chain on audit_log rows (Phase 2 of per-org migration).

Walks every row in `(org_id, id ASC)` order and populates `prev_hash_org`,
`entry_hash_org`, `org_chain_seq` from scratch — rewriting any values the
Phase 1 dual-write already set. This is correct because nothing reads the
per-org chain yet (Phase 3 cuts the verifier over).

Idempotent. Safe to re-run. Safe to interrupt — re-running picks up clean
because each org is processed atomically.

Concurrency: takes the same per-org PostgreSQL advisory lock as the writer
(see common/audit/writer.py:_get_last_org_chain_state). New rows in an org
block until that org's backfill commits. Other orgs continue writing
normally.

Trigger handling: `audit_log_no_update` blocks UPDATE on audit_log. We
disable it for the duration of the backfill and re-enable in `finally` so
a crash never leaves it disabled. The hourly health check
(scripts/check_audit_trigger.py) is the safety net if `finally` fails.

Usage:
    DATABASE_URL=postgresql://... python scripts/backfill_per_org_chain.py
    python scripts/backfill_per_org_chain.py --dry-run
    python scripts/backfill_per_org_chain.py --org-id <uuid>   # one org

Exit codes:
  0  success
  1  one or more orgs failed (others may have completed)
  2  config / connection error
"""

from __future__ import annotations

import argparse
import os
import sys
import time
import uuid
from typing import TYPE_CHECKING

# Make `common` importable when run as `python scripts/backfill_per_org_chain.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text, update  # noqa: E402

from common.audit.writer import GENESIS, _ensure_utc, compute_entry_hash_org  # noqa: E402
from common.models import Organization  # noqa: E402
from common.models.audit_log import AuditLog  # noqa: E402
from common.models.base import SessionLocal  # noqa: E402

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

TRIGGER_NAME = "audit_log_no_update"


def _list_orgs_with_rows(db: Session) -> list[uuid.UUID]:
    """Return distinct org_ids that have at least one audit_log row."""
    rows = db.execute(text("SELECT DISTINCT org_id FROM audit_log ORDER BY org_id")).all()
    return [r[0] if isinstance(r[0], uuid.UUID) else uuid.UUID(str(r[0])) for r in rows]


def _resolve_hmac_key(db: Session, org_id: uuid.UUID) -> str | None:
    """Return the org's forensic_verify_key, or None to fall back to the global key."""
    org = db.query(Organization).filter(Organization.id == org_id).first()
    if org and org.forensic_verify_key:
        return org.forensic_verify_key
    return None


def backfill_org(
    db: Session,
    org_id: uuid.UUID,
    *,
    dry_run: bool = False,
) -> tuple[int, int]:
    """Rewrite the per-org chain for one org.

    Returns (rows_processed, rows_changed). On dry_run, rows_changed is the
    number of rows that *would* have been updated.
    """
    dialect = db.bind.dialect.name if db.bind else "unknown"

    # Per-org advisory lock — blocks new writes for this org while we
    # rewrite. Released on commit/rollback. No-op on SQLite (test runs).
    if dialect == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('audit_chain:' || :org_id))"),
            {"org_id": str(org_id)},
        )

    hmac_key = _resolve_hmac_key(db, org_id)

    # Snapshot pre-state — used both to detect an idempotent re-run
    # (every row already has the right seq) and to count rows that
    # actually change. yield_per isn't worth the complexity for a list
    # we walk twice; orgs in practice are bounded.
    all_rows = (
        db.query(AuditLog).filter(AuditLog.org_id == org_id).order_by(AuditLog.id.asc()).all()
    )
    processed = len(all_rows)

    pre_state: list[tuple[int, str | None]] = [(r.id, r.org_chain_seq) for r in all_rows]

    # Fast path: every row already has the seq it would be assigned.
    # We trust that hashes/prev_hash_org are correct here — verifying
    # those is verify_per_org_chain.py's job. This makes a no-op re-run
    # cheap and gives the test suite a meaningful "changed=0" signal.
    already_correct = all(seq == (i + 1) for i, (_, seq) in enumerate(pre_state))
    if already_correct:
        if dry_run:
            db.rollback()
        else:
            db.commit()
        return processed, 0

    # Clear any existing chain state so the rewrite can't collide on
    # UNIQUE(org_id, org_chain_seq) when reassigning seqs from
    # dual-written Phase 1 rows. UPDATEs in SQLAlchemy are not deferred,
    # so two rows briefly holding the same seq would violate the index.
    db.execute(
        update(AuditLog)
        .where(AuditLog.org_id == org_id)
        .values(prev_hash_org=None, entry_hash_org=None, org_chain_seq=None)
    )
    db.flush()

    prev_hash_org = GENESIS
    for i, row in enumerate(all_rows, start=1):
        new_hash = compute_entry_hash_org(
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
            prev_hash_org=prev_hash_org,
            hmac_key=hmac_key,
        )
        row.prev_hash_org = prev_hash_org
        row.entry_hash_org = new_hash
        row.org_chain_seq = i
        prev_hash_org = new_hash

    # changed = count of rows whose pre-state seq differs from their
    # final position. Captures both legacy NULL → populated and
    # dual-written wrong-seq → correct-seq.
    changed = sum(1 for i, (_, seq) in enumerate(pre_state) if seq != (i + 1))

    if dry_run:
        db.rollback()
    else:
        db.commit()

    return processed, changed


def _toggle_trigger(db: Session, enabled: bool) -> None:
    """ENABLE or DISABLE audit_log_no_update. No-op on non-PG dialects."""
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect != "postgresql":
        return
    verb = "ENABLE" if enabled else "DISABLE"
    db.execute(text(f"ALTER TABLE audit_log {verb} TRIGGER {TRIGGER_NAME}"))
    db.commit()


def run(
    *,
    org_id: uuid.UUID | None,
    dry_run: bool,
) -> int:
    """Top-level entry point. Returns exit code."""
    db = SessionLocal()
    trigger_disabled = False
    failures: list[tuple[uuid.UUID, str]] = []

    try:
        if not dry_run:
            _toggle_trigger(db, enabled=False)
            trigger_disabled = True
            print(f"[backfill] disabled trigger {TRIGGER_NAME}")

        org_ids = [org_id] if org_id else _list_orgs_with_rows(db)
        print(f"[backfill] {len(org_ids)} org(s) to process (dry_run={dry_run})")

        total_processed = 0
        total_changed = 0

        for oid in org_ids:
            t0 = time.monotonic()
            try:
                processed, changed = backfill_org(db, oid, dry_run=dry_run)
                total_processed += processed
                total_changed += changed
                dt_ms = int((time.monotonic() - t0) * 1000)
                print(
                    f"[backfill] org={oid} processed={processed} "
                    f"changed={changed} duration_ms={dt_ms}"
                )
            except Exception as exc:  # noqa: BLE001
                db.rollback()
                failures.append((oid, repr(exc)))
                print(f"[backfill] org={oid} FAILED: {exc!r}", file=sys.stderr)

        print(
            f"[backfill] done — processed={total_processed} "
            f"changed={total_changed} failures={len(failures)}"
        )
        return 1 if failures else 0
    finally:
        if trigger_disabled:
            try:
                _toggle_trigger(db, enabled=True)
                print(f"[backfill] re-enabled trigger {TRIGGER_NAME}")
            except Exception as exc:  # noqa: BLE001
                print(
                    f"[backfill] CRITICAL: failed to re-enable trigger "
                    f"{TRIGGER_NAME}: {exc!r}. "
                    f"Run: ALTER TABLE audit_log ENABLE TRIGGER {TRIGGER_NAME}",
                    file=sys.stderr,
                )
        db.close()


def main() -> None:
    p = argparse.ArgumentParser(description="Backfill per-org audit chain")
    p.add_argument(
        "--dry-run",
        action="store_true",
        help="Compute the chain but don't write — leaves trigger enabled.",
    )
    p.add_argument(
        "--org-id",
        type=lambda s: uuid.UUID(s),
        default=None,
        help="Process only this org. Default: all orgs with rows.",
    )
    args = p.parse_args()

    rc = run(org_id=args.org_id, dry_run=args.dry_run)
    sys.exit(rc)


if __name__ == "__main__":
    main()
