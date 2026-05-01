"""SQLAlchemy base and engine setup."""

import logging
import time

import psycopg2
from sqlalchemy import create_engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.orm import DeclarativeBase, sessionmaker

from common.config.settings import settings

logger = logging.getLogger("ai_identity.common.db")

_IS_POSTGRES = settings.database_url.startswith(("postgres://", "postgresql://"))
_IS_NEON = "neon.tech" in settings.database_url


def _connect_with_retry():
    """Open a psycopg2 connection, retrying transient cold-start failures.

    Why: Neon scales compute to zero when idle. The first connection after a
    cold period can fail mid-handshake with `SSL SYSCALL error: EOF detected`
    while the compute spins up. pool_pre_ping doesn't help — the failure is on
    a brand-new connection, not a stale pooled one.
    """
    url = make_url(settings.database_url)
    kwargs = {
        "host": url.host,
        "port": url.port or 5432,
        "user": url.username,
        "password": url.password,
        "dbname": url.database,
        **({k: v for k, v in url.query.items()}),
    }
    if _IS_NEON:
        kwargs.setdefault("sslmode", "require")

    last_exc: Exception | None = None
    for attempt in range(3):
        try:
            return psycopg2.connect(**kwargs)
        except psycopg2.OperationalError as exc:
            last_exc = exc
            if attempt == 2:
                break
            delay = 0.5 * (2**attempt)
            logger.warning(
                "DB connect failed (attempt %d/3): %s — retrying in %.1fs",
                attempt + 1,
                exc,
                delay,
            )
            time.sleep(delay)
    assert last_exc is not None
    raise last_exc


_engine_kwargs: dict = {
    "echo": settings.debug,
    "pool_size": 10,
    "max_overflow": 20,
    "pool_timeout": 30,
    "pool_pre_ping": True,
    "pool_recycle": 300,
}
if _IS_POSTGRES:
    _engine_kwargs["creator"] = _connect_with_retry

engine = create_engine(settings.database_url, **_engine_kwargs)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """Declarative base for all models."""

    pass


def get_db():
    """FastAPI dependency — yields a DB session and closes it after the request."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
