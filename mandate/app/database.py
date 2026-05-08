"""MongoDB connection and index bootstrap for the Mandate Service.

Uses Motor (async PyMongo) with a single client instance per process.
Indexes are created at startup — idempotent, safe to run on every boot.

Collections:
  mandates        — live mandate documents
  mandate_events  — append-only revocation / expiry events (audit trail)
"""

import logging

from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from pymongo import ASCENDING, DESCENDING, IndexModel

from common.config.settings import settings

logger = logging.getLogger("ai_identity.mandate.db")

_client: AsyncIOMotorClient | None = None
_db: AsyncIOMotorDatabase | None = None

DB_NAME = "ai_identity_mandates"


def get_client() -> AsyncIOMotorClient:
    if _client is None:
        raise RuntimeError("MongoDB client not initialized — call init_db() first")
    return _client


def get_db() -> AsyncIOMotorDatabase:
    if _db is None:
        raise RuntimeError("MongoDB database not initialized — call init_db() first")
    return _db


async def init_db() -> None:
    """Connect to Atlas and create indexes. Called from the lifespan hook."""
    global _client, _db

    uri = settings.mongodb_uri
    if not uri:
        raise RuntimeError("MONGODB_URI is not configured")

    _client = AsyncIOMotorClient(
        uri,
        serverSelectionTimeoutMS=5000,
        connectTimeoutMS=5000,
        socketTimeoutMS=10000,
        maxPoolSize=20,
        retryWrites=True,
    )
    _db = _client[DB_NAME]

    await _ensure_indexes()
    logger.info("MongoDB connected — db=%s", DB_NAME)


async def close_db() -> None:
    global _client, _db
    if _client:
        _client.close()
        _client = None
        _db = None
        logger.info("MongoDB connection closed")


async def _ensure_indexes() -> None:
    db = get_db()

    mandate_indexes = [
        IndexModel([("mandate_id", ASCENDING)], unique=True, name="mandate_id_unique"),
        IndexModel([("subject.agent_id", ASCENDING)], name="subject_agent_id"),
        IndexModel([("subject.org_id", ASCENDING)], name="subject_org_id"),
        IndexModel([("issuer.org_id", ASCENDING)], name="issuer_org_id"),
        IndexModel([("status", ASCENDING)], name="status"),
        IndexModel(
            [("subject.agent_id", ASCENDING), ("status", ASCENDING)],
            name="subject_agent_status",
        ),
        IndexModel([("created_at", DESCENDING)], name="created_at_desc"),
        # Sparse index on valid_until so we can efficiently find expired mandates.
        # TTL auto-deletion is intentionally NOT used — we want to keep expired
        # mandate documents for audit purposes and just flip status = "expired".
        IndexModel(
            [("valid_until", ASCENDING)],
            sparse=True,
            name="valid_until_sparse",
        ),
    ]

    event_indexes = [
        IndexModel([("mandate_id", ASCENDING)], name="event_mandate_id"),
        IndexModel([("event_at", DESCENDING)], name="event_at_desc"),
    ]

    await db["mandates"].create_indexes(mandate_indexes)
    await db["mandate_events"].create_indexes(event_indexes)
    logger.debug("MongoDB indexes ensured")
