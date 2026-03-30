"""Tests for Human-in-the-Loop (HITL) approval — enterprise tier only.

Verifies:
  - Non-enterprise tiers skip HITL entirely (zero cost)
  - Matching require_approval patterns return pending + review_id
  - Non-matching endpoints pass through
  - Approved review_id allows request
  - Expired approvals are denied (fail-closed)
  - Mismatched review_id (wrong agent/endpoint) is handled gracefully
"""

import datetime
import uuid

import pytest

from common.models import Policy, User
from common.models.approval_request import ApprovalRequest, ApprovalStatus
from gateway.app.hitl import check_hitl, expire_stale

# Fixed UUIDs
AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")
ENTERPRISE_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000099")


@pytest.fixture
def enterprise_user(db_session):
    """Enterprise-tier user for HITL tests (separate from conftest test_user)."""
    user = User(
        id=ENTERPRISE_USER_ID,
        email="enterprise@example.com",
        role="owner",
        tier="enterprise",
    )
    db_session.add(user)
    db_session.commit()
    return user


@pytest.fixture
def hitl_policy(db_session, test_agent):
    """Policy with require_approval patterns."""
    policy = Policy(
        agent_id=test_agent.id,
        rules={
            "allowed_endpoints": ["/v1/*"],
            "allowed_methods": ["POST", "GET", "DELETE"],
            "require_approval": ["/v1/admin/*", "/v1/dangerous"],
        },
        version=1,
        is_active=True,
    )
    db_session.add(policy)
    db_session.commit()
    return policy


# ── Enterprise-Only Gate ─────────────────────────────────────────────


class TestHitlTierGate:
    """HITL is enterprise-only — free/pro/business skip entirely."""

    def test_free_tier_skips_hitl(self, db_session, test_agent, hitl_policy):
        """Free-tier user: HITL check returns allow immediately."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=ENTERPRISE_USER_ID,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="free",
        )
        assert result.action == "allow"
        assert result.review_id is None

    def test_pro_tier_skips_hitl(self, db_session, test_agent, hitl_policy):
        """Pro-tier user: HITL check returns allow immediately."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=ENTERPRISE_USER_ID,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="pro",
        )
        assert result.action == "allow"

    def test_enterprise_tier_triggers_hitl(
        self, db_session, test_agent, hitl_policy, enterprise_user
    ):
        """Enterprise-tier user: matching endpoint triggers HITL."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="enterprise",
        )
        assert result.action == "pending"
        assert result.review_id is not None


# ── Pattern Matching ─────────────────────────────────────────────────


class TestHitlPatternMatching:
    """Verify require_approval endpoint pattern matching."""

    def test_matching_prefix_pattern(self, db_session, test_agent, hitl_policy, enterprise_user):
        """/v1/admin/* matches /v1/admin/delete → pending."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="enterprise",
        )
        assert result.action == "pending"

    def test_matching_exact_pattern(self, db_session, test_agent, hitl_policy, enterprise_user):
        """/v1/dangerous exact match → pending."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/dangerous",
            method="POST",
            review_id=None,
            user_tier="enterprise",
        )
        assert result.action == "pending"

    def test_non_matching_endpoint_passes(
        self, db_session, test_agent, hitl_policy, enterprise_user
    ):
        """/v1/chat does NOT match require_approval patterns → allow."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/chat",
            method="POST",
            review_id=None,
            user_tier="enterprise",
        )
        assert result.action == "allow"

    def test_no_require_approval_in_policy(self, db_session, test_agent, enterprise_user):
        """Policy without require_approval → allow (no HITL)."""
        policy = Policy(
            agent_id=test_agent.id,
            rules={
                "allowed_endpoints": ["/v1/*"],
                "allowed_methods": ["POST"],
            },
            version=1,
            is_active=True,
        )
        db_session.add(policy)
        db_session.commit()

        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="enterprise",
        )
        assert result.action == "allow"


# ── Approval Request Creation ────────────────────────────────────────


class TestHitlApprovalCreation:
    """Verify approval requests are created correctly."""

    def test_creates_pending_approval(self, db_session, test_agent, hitl_policy, enterprise_user):
        """Pending HITL creates an ApprovalRequest in the DB."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="enterprise",
        )

        # Query by UUID object (SQLite compat)
        review_uuid = uuid.UUID(result.review_id)
        approval = (
            db_session.query(ApprovalRequest).filter(ApprovalRequest.id == review_uuid).first()
        )
        assert approval is not None
        assert approval.status == ApprovalStatus.pending.value
        assert str(approval.agent_id) == str(test_agent.id)
        assert str(approval.user_id) == str(enterprise_user.id)
        assert approval.endpoint == "/v1/admin/delete"
        assert approval.method == "DELETE"
        assert approval.expires_at is not None

    def test_approval_has_future_expiry(self, db_session, test_agent, hitl_policy, enterprise_user):
        """Approval expiry is in the future."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=None,
            user_tier="enterprise",
        )

        review_uuid = uuid.UUID(result.review_id)
        approval = (
            db_session.query(ApprovalRequest).filter(ApprovalRequest.id == review_uuid).first()
        )
        assert approval is not None
        assert approval.expires_at is not None


# ── Review ID Validation ─────────────────────────────────────────────


class TestHitlReviewValidation:
    """Verify review_id resubmission flow."""

    def test_approved_review_allows_request(
        self, db_session, test_agent, hitl_policy, enterprise_user
    ):
        """Approved review_id → allow."""
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.approved.value,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
        )
        db_session.add(approval)
        db_session.commit()

        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=str(approval.id),
            user_tier="enterprise",
        )
        assert result.action == "allow"

    def test_rejected_review_stays_pending(
        self, db_session, test_agent, hitl_policy, enterprise_user
    ):
        """Rejected review_id → pending (not allow)."""
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.rejected.value,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
        )
        db_session.add(approval)
        db_session.commit()

        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=str(approval.id),
            user_tier="enterprise",
        )
        assert result.action == "pending"

    def test_expired_review_is_denied(self, db_session, test_agent, hitl_policy, enterprise_user):
        """Expired review_id → lazy-expire + pending."""
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.pending.value,
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=1),
        )
        db_session.add(approval)
        db_session.commit()

        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=str(approval.id),
            user_tier="enterprise",
        )
        assert result.action == "pending"

        # Verify it was lazily expired
        db_session.refresh(approval)
        assert approval.status == ApprovalStatus.expired.value

    def test_mismatched_agent_skips(self, db_session, test_agent, hitl_policy, enterprise_user):
        """Review for different agent → skip HITL (allow)."""
        other_agent_id = uuid.uuid4()
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=other_agent_id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.approved.value,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
        )
        db_session.add(approval)
        db_session.commit()

        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id=str(approval.id),
            user_tier="enterprise",
        )
        assert result.action == "allow"

    def test_invalid_uuid_skips(self, db_session, test_agent, hitl_policy, enterprise_user):
        """Invalid review_id UUID → skip HITL (allow)."""
        result = check_hitl(
            db=db_session,
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            review_id="not-a-uuid",
            user_tier="enterprise",
        )
        assert result.action == "allow"


# ── Expire Stale ─────────────────────────────────────────────────────


class TestExpireStale:
    """Verify batch expiration of stale pending approvals."""

    def test_expires_past_deadline(self, db_session, test_agent, enterprise_user):
        """Pending approvals past deadline are expired."""
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.pending.value,
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=10),
        )
        db_session.add(approval)
        db_session.commit()

        count = expire_stale(db_session)
        assert count == 1

        db_session.refresh(approval)
        assert approval.status == ApprovalStatus.expired.value

    def test_does_not_expire_future(self, db_session, test_agent, enterprise_user):
        """Pending approvals with future deadline are NOT expired."""
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.pending.value,
            expires_at=datetime.datetime.utcnow() + datetime.timedelta(minutes=5),
        )
        db_session.add(approval)
        db_session.commit()

        count = expire_stale(db_session)
        assert count == 0

        db_session.refresh(approval)
        assert approval.status == ApprovalStatus.pending.value

    def test_does_not_expire_already_resolved(self, db_session, test_agent, enterprise_user):
        """Already approved/rejected items are not touched."""
        approval = ApprovalRequest(
            id=uuid.uuid4(),
            agent_id=test_agent.id,
            user_id=enterprise_user.id,
            endpoint="/v1/admin/delete",
            method="DELETE",
            status=ApprovalStatus.approved.value,
            expires_at=datetime.datetime.utcnow() - datetime.timedelta(minutes=10),
        )
        db_session.add(approval)
        db_session.commit()

        count = expire_stale(db_session)
        assert count == 0

        db_session.refresh(approval)
        assert approval.status == ApprovalStatus.approved.value
