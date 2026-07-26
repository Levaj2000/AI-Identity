"""Protected-user allowlist after the public-repo scrub (2026-07-26).

The allowlist used to hardcode two personal Gmail addresses in
common/queries/user_cleanup.py. This repo is PUBLIC, so the plaintext was
removed — but naively deleting it would have made those accounts eligible for
the weekly cleanup cron. Protection is now two-layered: an env-configured list
plus a hard-coded SHA-256 backstop.

The invariant these tests defend: an unset or empty PROTECTED_EMAILS env var
must never mean "protect nobody".

These tests deliberately use a SYNTHETIC address injected into the backstop.
Writing the real ones here would republish exactly what the scrub removed — a
test file is no better a place for them than production code.

See docs/security/public-repo-exposure-remediation.md.
"""

import hashlib
import importlib
import uuid

import pytest

from common.models.user import User
from common.queries import user_cleanup
from common.queries.user_cleanup import delete_users_with_cascade, is_protected

# Synthetic stand-in for a backstopped account.
SYNTHETIC = "protected-fixture@example.test"
SYNTHETIC_HASH = hashlib.sha256(SYNTHETIC.encode()).hexdigest()


@pytest.fixture
def backstop(monkeypatch):
    """Replace the real backstop with a synthetic one for the duration."""
    monkeypatch.setattr(user_cleanup, "_PROTECTED_EMAIL_HASHES", frozenset({SYNTHETIC_HASH}))
    return SYNTHETIC


def test_backstop_is_populated():
    """The shipped backstop must not be empty — that is the whole safety net."""
    assert len(user_cleanup._PROTECTED_EMAIL_HASHES) == 2
    assert all(len(h) == 64 for h in user_cleanup._PROTECTED_EMAIL_HASHES)


def test_empty_env_still_protects(backstop, monkeypatch):
    """An unset env var must not collapse protection to nothing."""
    monkeypatch.setattr(user_cleanup, "PROTECTED_EMAILS", set())
    assert user_cleanup.is_protected(backstop)


def test_env_var_parsing(monkeypatch):
    monkeypatch.setenv("PROTECTED_EMAILS", "keep-me@example.com, Other@Example.COM")
    reloaded = importlib.reload(user_cleanup)
    try:
        # Entries are normalized on both sides.
        assert sorted(reloaded.PROTECTED_EMAILS) == [
            "keep-me@example.com",
            "other@example.com",
        ]
        assert reloaded.is_protected("KEEP-ME@example.com")
        assert not reloaded.is_protected("delete-me@example.com")
    finally:
        # Clear the env var BEFORE reloading — monkeypatch tears down after the
        # test returns, so reloading first would bake the test value into module
        # state for the rest of the session.
        monkeypatch.delenv("PROTECTED_EMAILS", raising=False)
        importlib.reload(user_cleanup)


def test_blank_env_var_yields_empty_set(monkeypatch):
    monkeypatch.setenv("PROTECTED_EMAILS", "   ,  ,")
    reloaded = importlib.reload(user_cleanup)
    try:
        assert not reloaded.PROTECTED_EMAILS
    finally:
        monkeypatch.delenv("PROTECTED_EMAILS", raising=False)
        importlib.reload(user_cleanup)


def test_matching_is_case_and_whitespace_insensitive(backstop):
    """Strictly more protective than the old exact set-membership test."""
    assert user_cleanup.is_protected(backstop)
    assert user_cleanup.is_protected(backstop.upper())
    assert user_cleanup.is_protected(f"  {backstop}  ")


@pytest.mark.parametrize("email", ["not-protected@example.com", "", None])
def test_unprotected_addresses(email):
    assert not is_protected(email)


def test_delete_skips_protected_users(db_session, backstop):
    """The safety net in delete_users_with_cascade honours the backstop.

    Passing ONLY the protected user is deliberate: the protection filter
    empties the list and the function returns before reaching the
    Postgres-only ``ALTER TABLE ... DISABLE TRIGGER``, so this stays runnable
    on the sqlite test database. A non-empty list going in and zero deletions
    coming out is exactly the invariant — the empty-input guard above the
    filter cannot account for it.
    """
    protected = User(id=uuid.uuid4(), email=backstop, role="member", tier="free")
    db_session.add(protected)
    db_session.commit()

    result = delete_users_with_cascade(db_session, [protected])

    assert result["deleted_count"] == 0
    assert result["emails"] == []
    assert db_session.query(User).filter(User.id == protected.id).first() is not None
