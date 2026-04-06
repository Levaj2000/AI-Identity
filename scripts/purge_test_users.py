"""One-time script to purge test/seed users from the database.

Targets users matching test patterns while protecting real accounts.
Dry-run by default — pass --execute to actually delete.

Usage:
    python scripts/purge_test_users.py              # dry-run
    python scripts/purge_test_users.py --execute    # delete for real
"""

import argparse
import os
import sys

# Add project root to path so common/ is importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import or_  # noqa: E402

from common.models import Agent, SessionLocal, User  # noqa: E402
from common.queries.user_cleanup import PROTECTED_EMAILS, delete_users_with_cascade  # noqa: E402

# Patterns that identify test/seed users
TEST_PATTERNS = [
    "%@test.ai-identity.co",  # qa-client-* onboarding sims
    "%@ai-identity.local",  # seed-dev
    "test-dev-key-%",  # legacy test key "user"
]

TEST_EXACT = [
    "testclient@ai-identity.co",
]


def find_test_users(db):
    """Find users matching test patterns, excluding protected emails."""
    filters = [User.email.like(p) for p in TEST_PATTERNS]
    filters.extend(User.email == e for e in TEST_EXACT)

    users = db.query(User).filter(or_(*filters)).filter(User.email.notin_(PROTECTED_EMAILS)).all()
    return users


def main():
    parser = argparse.ArgumentParser(description="Purge test users from the database")
    parser.add_argument(
        "--execute",
        action="store_true",
        help="Actually delete (default is dry-run)",
    )
    args = parser.parse_args()

    db = SessionLocal()
    try:
        users = find_test_users(db)

        if not users:
            print("No test users found. Nothing to do.")
            return

        print(f"{'=' * 60}")
        print(f"  Test User Purge — {'EXECUTE' if args.execute else 'DRY RUN'}")
        print(f"{'=' * 60}")
        print()

        for user in users:
            agent_count = db.query(Agent).filter(Agent.user_id == user.id).count()
            print(f"  {user.email}")
            print(f"    ID: {user.id}")
            print(f"    Tier: {user.tier} | Role: {user.role}")
            print(f"    Agents: {agent_count}")
            print(f"    Created: {user.created_at}")
            print()

        print(f"Total: {len(users)} test users to delete")
        print(f"Protected: {', '.join(PROTECTED_EMAILS)}")
        print()

        if not args.execute:
            print("This is a DRY RUN. Pass --execute to delete these users.")
            return

        result = delete_users_with_cascade(db, users)
        print(
            f"Deleted {result['deleted_count']} users ({result['agents_removed']} agents cascaded)"
        )
        print(f"Emails: {', '.join(result['emails'])}")

    finally:
        db.close()


if __name__ == "__main__":
    main()
