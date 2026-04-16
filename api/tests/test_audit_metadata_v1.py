"""Tests for the versioned AuditMetadataV1 schema + writer integration.

Covers:
  - Schema validates and round-trips
  - `is_v1` / `as_metadata_dict` detect and serialize correctly
  - Writer accepts both dict (legacy) and AuditMetadataV1 (new)
  - correlation_id on v1 metadata promotes to the top-level column
  - contextvar auto-resolves correlation_id when caller doesn't pass one
  - HMAC chain still verifies with correlation_id present (it's NOT in the
    canonical payload — same policy as user_id / org_id)
"""

import uuid

from common.audit import create_audit_entry, verify_chain
from common.audit.correlation import (
    reset_current_correlation_id,
    set_current_correlation_id,
)
from common.models import Agent, User
from common.schemas.audit_metadata import (
    Actor,
    AuditMetadataV1,
    Cost,
    PolicyTrace,
    Tenant,
    as_metadata_dict,
    is_v1,
)

# ── Schema round-trip ────────────────────────────────────────────────


class TestSchemaRoundTrip:
    def test_minimal_v1_validates(self):
        m = AuditMetadataV1()
        assert m.schema_version == 1
        assert m.correlation_id is None
        assert m.actor is None

    def test_full_v1_round_trips(self):
        cid = str(uuid.uuid4())
        m = AuditMetadataV1(
            correlation_id=cid,
            actor=Actor(type="user", id="u-123", email="a@b.co"),
            tenant=Tenant(org_id=uuid.uuid4(), user_id=uuid.uuid4()),
            policy_trace=PolicyTrace(matched_rules=["r1"], dry_run=True),
            cost=Cost(model="gpt-4", input_tokens=10, output_tokens=5),
            latency_ms=42,
        )
        dumped = m.model_dump(mode="json", exclude_none=True)
        restored = AuditMetadataV1.model_validate(dumped)
        assert restored.correlation_id == cid
        assert restored.actor.id == "u-123"
        assert restored.cost.model == "gpt-4"

    def test_extra_keys_preserved(self):
        """Unknown top-level keys survive validation (extra='allow')."""
        m = AuditMetadataV1.model_validate(
            {
                "schema_version": 1,
                "correlation_id": "abc",
                "action_type": "agent_created",  # legacy key
                "keys_revoked": 3,
            }
        )
        dumped = m.model_dump(mode="json", exclude_none=True)
        assert dumped["action_type"] == "agent_created"
        assert dumped["keys_revoked"] == 3

    def test_correlation_id_length_limit_enforced(self):
        import pytest
        from pydantic import ValidationError

        too_long = "x" * 65
        with pytest.raises(ValidationError):
            AuditMetadataV1(correlation_id=too_long)


class TestHelpers:
    def test_is_v1_detects_tag(self):
        assert is_v1({"schema_version": 1, "foo": "bar"}) is True
        assert is_v1({"foo": "bar"}) is False
        assert is_v1(None) is False
        assert is_v1({}) is False

    def test_as_metadata_dict_stamps_version(self):
        m = AuditMetadataV1(correlation_id="abc")
        dumped = as_metadata_dict(m)
        assert dumped["schema_version"] == 1
        assert dumped["correlation_id"] == "abc"

    def test_as_metadata_dict_passes_through_legacy(self):
        legacy = {"model": "gpt-4", "action_type": "chat"}
        dumped = as_metadata_dict(legacy)
        assert dumped == legacy  # unchanged, no stamp
        assert "schema_version" not in dumped

    def test_as_metadata_dict_none_becomes_empty(self):
        assert as_metadata_dict(None) == {}


# ── Writer integration ──────────────────────────────────────────────


AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


def _seed_agent(db):
    """Minimal agent for writer tests — no org (writer falls back to system)."""
    user = User(
        id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        email="writer-test@test",
        role="owner",
        tier="enterprise",
    )
    db.add(user)
    db.flush()
    agent = Agent(
        id=AGENT_ID,
        user_id=user.id,
        name="Writer Test Agent",
        status="active",
        capabilities=[],
        metadata_={},
    )
    db.add(agent)
    db.commit()
    return agent


class TestWriterAcceptsBothShapes:
    def test_legacy_dict_still_works(self, db_session):
        _seed_agent(db_session)
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={"model": "gpt-4", "action_type": "chat"},
        )
        # No schema_version stamped on legacy dicts (unless caller included cid)
        assert "schema_version" not in entry.request_metadata
        assert entry.request_metadata["model"] == "gpt-4"

    def test_v1_metadata_promotes_correlation_id_to_column(self, db_session):
        _seed_agent(db_session)
        cid = str(uuid.uuid4())
        meta = AuditMetadataV1(
            correlation_id=cid,
            actor=Actor(type="user", id="u-1"),
        )
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata=meta,
        )
        assert entry.correlation_id == cid
        assert entry.request_metadata["schema_version"] == 1
        assert entry.request_metadata["correlation_id"] == cid

    def test_explicit_correlation_kwarg_wins(self, db_session):
        _seed_agent(db_session)
        explicit_cid = "explicit-cid"
        meta = AuditMetadataV1(correlation_id="from-the-model")
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata=meta,
            correlation_id=explicit_cid,
        )
        assert entry.correlation_id == explicit_cid


class TestContextVarAutoResolve:
    def test_middleware_contextvar_flows_to_writer(self, db_session):
        """When nothing is passed, the writer pulls correlation_id from the contextvar."""
        _seed_agent(db_session)
        cid = str(uuid.uuid4())
        token = set_current_correlation_id(cid)
        try:
            entry = create_audit_entry(
                db_session,
                agent_id=AGENT_ID,
                endpoint="/v1/chat",
                method="POST",
                decision="allow",
                request_metadata={"model": "gpt-4"},
            )
        finally:
            reset_current_correlation_id(token)

        assert entry.correlation_id == cid
        # Legacy dict stays untagged — we did NOT retroactively mark it v1
        # just because the contextvar had a value.
        assert "schema_version" not in entry.request_metadata

    def test_no_contextvar_no_correlation_id(self, db_session):
        _seed_agent(db_session)
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={},
        )
        assert entry.correlation_id is None


class TestHmacChainIntact:
    def test_hmac_chain_verifies_with_correlation_ids(self, db_session):
        """correlation_id is NOT in the canonical payload. Chain must verify."""
        _seed_agent(db_session)

        for i in range(4):
            token = set_current_correlation_id(f"cid-{i}")
            try:
                create_audit_entry(
                    db_session,
                    agent_id=AGENT_ID,
                    endpoint=f"/v1/chat/{i}",
                    method="POST",
                    decision="allow",
                    request_metadata={"seq": i},
                )
            finally:
                reset_current_correlation_id(token)

        result = verify_chain(db_session)
        assert result.valid is True
        assert result.entries_verified == 4
