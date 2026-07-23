"""Backfill audit_log.key_fingerprint on rows written before epoch tracking.

Each audit row is now stamped at write time with the fingerprint of the
HMAC key that hashed it (see common/audit/writer.py:key_fingerprint).
Legacy rows have NULL — this script determines which key epoch each one
belongs to by recomputing its stored hash against every key the server
holds for the org (current forensic_verify_key, retired keys from
forensic_key_history, and the global platform key), then stamps the
matching fingerprint.

METADATA-ONLY: this never touches entry_hash / entry_hash_org /
prev_hash* — no stored hash is rewritten, so previously exported bundles
stay valid and the append-only forensic posture holds. The fingerprint is
derived data, recoverable at any time by re-running this script.

Idempotent. Safe to re-run (only NULL fingerprints are considered). Rows
whose hash matches no held key are left NULL and reported — they indicate
either tampering or a key that was discarded before key history existed;
investigate with scripts/verify_per_org_chain.py.

Trigger handling: `audit_log_no_update` blocks UPDATE on audit_log. We
disable it for the duration of the backfill and re-enable in `finally`,
same as scripts/backfill_per_org_chain.py.

Usage:
    DATABASE_URL=postgresql://... python scripts/backfill_key_fingerprints.py
    python scripts/backfill_key_fingerprints.py --dry-run
    python scripts/backfill_key_fingerprints.py --org-id <uuid>   # one org

Exit codes:
  0  success (all considered rows stamped, or nothing to do)
  1  one or more rows matched no held key (left NULL) or an org failed
  2  config / connection error
"""

from __future__ import annotations

import argparse
import os
import sys
import uuid
from typing import TYPE_CHECKING

# Make `common` importable when run as `python scripts/backfill_key_fingerprints.py`
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text  # noqa: E402

from common.audit.writer import (  # noqa: E402
    _ensure_utc,
    _org_key_candidates,
    compute_entry_hash,
    compute_entry_hash_org,
)
from common.models.audit_log import AuditLog  # noqa: E402
from common.models.base import SessionLocal  # noqa: E402

if TYPE_CHECKING:
    from sqlalchemy.orm import Session

TRIGGER_NAME = "audit_log_no_update"


def _list_orgs_with_unstamped_rows(db: Session) -> list[uuid.UUID]:
    """Return distinct org_ids that still have rows without a fingerprint."""
    rows = db.execute(
        text("SELECT DISTINCT org_id FROM audit_log WHERE key_fingerprint IS NULL ORDER BY org_id")
    ).all()
    return [r[0] if isinstance(r[0], uuid.UUID) else uuid.UUID(str(r[0])) for r in rows]


def _match_fingerprint(row: AuditLog, candidates: list[tuple[str, str | None]]) -> str | None:
    """Return the fingerprint of the key that recomputes this row's stored hash.

    Prefers the per-org chain hash when the row has one; falls back to the
    global-chain hash for rows that predate the per-org migration. Both are
    hashed under the same key at write time, so either is a valid witness.
    """
    common_kwargs = dict(
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
    )
    for fp, key in candidates:
        if row.entry_hash_org is not None:
            recomputed = compute_entry_hash_org(
                **common_kwargs, prev_hash_org=row.prev_hash_org, hmac_key=key
            )
            if recomputed == row.entry_hash_org:
                return fp
        recomputed = compute_entry_hash(**common_kwargs, prev_hash=row.prev_hash, hmac_key=key)
        if recomputed == row.entry_hash:
            return fp
    return None


def backfill_org(db: Session, org_id: uuid.UUID, *, dry_run: bool = False) -> tuple[int, int, int]:
    """Stamp fingerprints for one org's unstamped rows.

    Returns (rows_processed, rows_stamped, rows_unmatched). On dry_run,
    rows_stamped is the number that *would* have been stamped.
    """
    dialect = db.bind.dialect.name if db.bind else "unknown"

    # Same per-org advisory lock as the writer — freezes the org's chain
    # tail while we walk it. Released on commit/rollback.
    if dialect == "postgresql":
        db.execute(
            text("SELECT pg_advisory_xact_lock(hashtext('audit_chain:' || :org_id))"),
            {"org_id": str(org_id)},
        )

    candidates = _org_key_candidates(db, org_id)

    rows = (
        db.query(AuditLog)
        .filter(AuditLog.org_id == org_id)
        .filter(AuditLog.key_fingerprint.is_(None))
        .order_by(AuditLog.id.asc())
        .all()
    )
    processed = len(rows)
    stamped = 0
    unmatched = 0

    for row in rows:
        fp = _match_fingerprint(row, candidates)
        if fp is None:
            unmatched += 1
            print(
                f"  [warn] org {org_id} row id={row.id}: stored hash matches "
                f"none of the {len(candidates)} held keys — left NULL"
            )
            continue
        stamped += 1
        if not dry_run:
            row.key_fingerprint = fp

    if dry_run:
        db.rollback()  # release advisory lock, discard nothing
    else:
        db.commit()
    return processed, stamped, unmatched


def _toggle_trigger(db: Session, enabled: bool) -> None:
    """ENABLE or DISABLE audit_log_no_update. No-op on non-PG dialects."""
    dialect = db.bind.dialect.name if db.bind else "unknown"
    if dialect != "postgresql":
        return
    verb = "ENABLE" if enabled else "DISABLE"
    db.execute(text(f"ALTER TABLE audit_log {verb} TRIGGER {TRIGGER_NAME}"))
    db.commit()


def run(*, org_id: uuid.UUID | None, dry_run: bool) -> int:
    """Top-level entry point. Returns exit code."""
    db = SessionLocal()
    trigger_disabled = False
    failures: list[tuple[uuid.UUID, str]] = []
    total_unmatched = 0

    try:
        if not dry_run:
            _toggle_trigger(db, enabled=False)
            trigger_disabled = True
            print(f"[backfill] disabled trigger {TRIGGER_NAME}")

        org_ids = [org_id] if org_id else _list_orgs_with_unstamped_rows(db)
        print(f"[backfill] {len(org_ids)} org(s) with unstamped rows (dry_run={dry_run})")

        total_processed = 0
        total_stamped = 0

        for oid in org_ids:
            try:
                processed, stamped, unmatched = backfill_org(db, oid, dry_run=dry_run)
                total_processed += processed
                total_stamped += stamped
                total_unmatched += unmatched
                print(
                    f"[backfill] org {oid}: {processed} rows, "
                    f"{stamped} stamped, {unmatched} unmatched"
                )
            except Exception as exc:  # keep going; report at the end
                db.rollback()
                failures.append((oid, str(exc)))
                print(f"[backfill] org {oid} FAILED: {exc}", file=sys.stderr)

        print(
            f"[backfill] done: {total_processed} rows processed, "
            f"{total_stamped} stamped, {total_unmatched} unmatched, "
            f"{len(failures)} org(s) failed"
        )
    finally:
        if trigger_disabled:
            _toggle_trigger(db, enabled=True)
            print(f"[backfill] re-enabled trigger {TRIGGER_NAME}")
        db.close()

    return 1 if failures or total_unmatched else 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dry-run", action="store_true", help="Report only; write nothing")
    parser.add_argument("--org-id", type=uuid.UUID, default=None, help="Backfill a single org")
    args = parser.parse_args()

    try:
        return run(org_id=args.org_id, dry_run=args.dry_run)
    except Exception as exc:
        print(f"[backfill] fatal: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
