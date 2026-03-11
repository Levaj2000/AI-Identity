"""Agent model — core identity entity."""

import datetime

from sqlalchemy import Boolean, Column, DateTime, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB

from common.models.base import Base


class Agent(Base):
    """An AI agent with its own identity, API key, and capabilities."""

    __tablename__ = "agents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)

    # API key — SHA-256 hash stored, prefix for identification
    key_hash = Column(String(64), nullable=False, unique=True, index=True)
    key_prefix = Column(String(20), nullable=False)  # e.g. "aid_sk_abc1"

    # Rotation — previous key hash during grace period
    previous_key_hash = Column(String(64), nullable=True)
    key_rotated_at = Column(DateTime, nullable=True)

    # Capabilities & policies
    capabilities = Column(JSONB, nullable=False, default=list)
    policies = Column(JSONB, nullable=False, default=dict)

    # Status
    is_active = Column(Boolean, nullable=False, default=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.datetime.utcnow)
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.datetime.utcnow,
        onupdate=datetime.datetime.utcnow,
    )
