"""Seed script — creates sample agents and keys for local development.

Creates 3 sample agents (ChatBot Alpha, Data Analyst, Image Creator) each
with one active API key and realistic metadata. Idempotent — safe to run
multiple times without duplicating data.

Usage:
    python scripts/seed.py              # seed using DATABASE_URL from .env
    DATABASE_URL=sqlite:///local.db python scripts/seed.py  # override DB
"""

import os
import sys
import uuid

# Add project root to path so common/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from common.auth.keys import generate_api_key, get_key_prefix, hash_key  # noqa: E402
from common.config.settings import settings  # noqa: E402
from common.models import (  # noqa: E402
    Agent,
    AgentKey,
    AgentStatus,
    Base,
    KeyStatus,
    SessionLocal,
    User,
    engine,
)

# ── Seed Data ────────────────────────────────────────────────────────────

SEED_USER_EMAIL = "seed-dev@ai-identity.local"

SEED_AGENTS = [
    {
        "name": "ChatBot Alpha",
        "description": "General-purpose conversational agent for customer support",
        "capabilities": ["chat_completion"],
        "metadata": {
            "framework": "langchain",
            "environment": "development",
            "owner_team": "support",
        },
    },
    {
        "name": "Data Analyst",
        "description": "Runs data queries and generates reports with code execution",
        "capabilities": ["function_calling", "code_execution"],
        "metadata": {
            "framework": "crewai",
            "environment": "staging",
            "owner_team": "analytics",
        },
    },
    {
        "name": "Image Creator",
        "description": "Generates and edits images from text prompts",
        "capabilities": ["image_generation"],
        "metadata": {
            "framework": "custom",
            "environment": "production",
            "owner_team": "creative",
        },
    },
]


# ── Seed Logic ───────────────────────────────────────────────────────────


def _ensure_tables_exist():
    """Create tables if they don't exist (for local SQLite usage)."""
    if "sqlite" in settings.database_url:
        # SQLite needs type remapping for JSONB/UUID columns
        from sqlalchemy import JSON, UUID, Uuid
        from sqlalchemy.dialects.postgresql import JSONB

        for table in Base.metadata.tables.values():
            for column in table.columns:
                if isinstance(column.type, JSONB):
                    column.type = JSON()
                elif isinstance(column.type, UUID):
                    column.type = Uuid()

    Base.metadata.create_all(bind=engine)


def _get_or_create_user(session) -> User:
    """Get existing seed user or create one. Returns the User."""
    user = session.query(User).filter(User.email == SEED_USER_EMAIL).first()
    if user:
        print(f"  User already exists: {user.email} ({user.id})")
        return user

    user = User(
        id=uuid.uuid4(),
        email=SEED_USER_EMAIL,
        role="owner",
    )
    session.add(user)
    session.flush()
    print(f"  Created user: {user.email} ({user.id})")
    return user


def _seed_agent(session, user: User, agent_data: dict) -> tuple:
    """Create an agent + key if it doesn't already exist.

    Returns (agent, plaintext_key, created) where created is True if new.
    """
    # Check for existing agent by name + user
    existing = (
        session.query(Agent)
        .filter(Agent.user_id == user.id, Agent.name == agent_data["name"])
        .first()
    )
    if existing:
        return existing, None, False

    agent = Agent(
        id=uuid.uuid4(),
        user_id=user.id,
        name=agent_data["name"],
        description=agent_data["description"],
        status=AgentStatus.active.value,
        capabilities=agent_data["capabilities"],
        metadata_=agent_data["metadata"],
    )
    session.add(agent)
    session.flush()

    # Generate the initial API key
    plaintext_key = generate_api_key()
    agent_key = AgentKey(
        agent_id=agent.id,
        key_hash=hash_key(plaintext_key),
        key_prefix=get_key_prefix(plaintext_key),
        status=KeyStatus.active.value,
    )
    session.add(agent_key)
    session.flush()

    return agent, plaintext_key, True


def main():
    """Seed the database with sample agents and keys."""
    print("Seeding AI Identity database...")
    print(f"  Database: {settings.database_url[:50]}...")
    print()

    _ensure_tables_exist()

    session = SessionLocal()
    try:
        # 1. Ensure seed user exists
        user = _get_or_create_user(session)
        print()

        # 2. Create agents
        created_count = 0
        skipped_count = 0

        for agent_data in SEED_AGENTS:
            agent, plaintext_key, created = _seed_agent(session, user, agent_data)

            if created:
                created_count += 1
                print(f"  Created: {agent.name}")
                print(f"    ID:           {agent.id}")
                print(f"    Capabilities: {agent.capabilities}")
                print(f"    Metadata:     {agent.metadata_}")
                print(f"    API Key:      {plaintext_key}")
                print(f"    Key Prefix:   {get_key_prefix(plaintext_key)}")
                print()
            else:
                skipped_count += 1
                # Show existing agent info
                key = (
                    session.query(AgentKey)
                    .filter(
                        AgentKey.agent_id == agent.id,
                        AgentKey.status == KeyStatus.active.value,
                    )
                    .first()
                )
                prefix = key.key_prefix if key else "(no active key)"
                print(f"  Exists:  {agent.name} ({agent.id}) — key: {prefix}")

        session.commit()

        # Summary
        print()
        print(f"Done: {created_count} created, {skipped_count} already existed.")

    except Exception as e:
        session.rollback()
        print(f"Error: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
