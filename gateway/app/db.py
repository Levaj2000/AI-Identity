"""Gateway-specific database dependency with RLS service bypass.

The gateway processes requests on behalf of agents (not users), so it
cannot set app.current_user_id. Instead, it sets app.is_service = 'true'
which activates the service_bypass RLS policy on all tenant tables.

This ensures the gateway can read/write across all tenants (needed for
policy evaluation and audit logging) while the API's user-scoped sessions
are restricted to a single tenant.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import text

from common.models.base import SessionLocal

if TYPE_CHECKING:
    from sqlalchemy.orm import Session


def get_gateway_db():
    """Yield a DB session with the RLS service bypass flag set.

    SET LOCAL is transaction-scoped — resets on commit/rollback.
    On SQLite (tests), the SET LOCAL is skipped.
    """
    db: Session = SessionLocal()
    try:
        dialect = db.bind.dialect.name if db.bind else "unknown"
        if dialect == "postgresql":
            db.execute(text("SET LOCAL app.is_service = 'true'"))
        yield db
    finally:
        db.close()
