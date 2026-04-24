"""Tests for audit log hygiene — metadata allowlist, PII rejection, debug logging.

SECURITY-CRITICAL: These tests verify that:
  - Only allowlisted metadata keys reach the audit_log table
  - PII fields are blocked and logged as security events
  - Request/response bodies are NEVER stored
  - Debug logging applies PII redaction
  - The sanitizer is wired into create_audit_entry
  - A PII scan of audit entries returns zero hits
"""

import uuid
from unittest.mock import patch

import pytest

from common.audit.debug_log import redact_dict, redact_pii
from common.audit.sanitizer import (
    ALLOWED_METADATA_KEYS,
    MAX_METADATA_VALUE_LENGTH,
    PII_FIELD_BLOCKLIST,
    is_pii_field,
    sanitize_metadata,
)
from common.audit.writer import create_audit_entry

AGENT_ID = uuid.UUID("00000000-0000-0000-0000-000000000010")


# ── Metadata Allowlist ──────────────────────────────────────────────────


class TestMetadataAllowlist:
    """Test that only allowlisted metadata keys pass through."""

    def test_allowed_keys_pass(self):
        """All allowlisted keys survive sanitization."""
        metadata = {
            "deny_reason": "policy_denied",
            "status_code": 403,
            "key_type": "runtime",
            "latency_ms": 42,
            "model": "gpt-4",
            "token_count": 150,
            "cost_estimate_usd": 0.003,
            "policy_version": 2,
        }
        result = sanitize_metadata(metadata)
        assert result == metadata

    def test_unknown_keys_stripped(self):
        """Keys not in the allowlist are silently removed."""
        metadata = {
            "status_code": 200,
            "rogue_field": "should_not_persist",
            "another_unknown": 42,
        }
        result = sanitize_metadata(metadata)
        assert result == {"status_code": 200}
        assert "rogue_field" not in result
        assert "another_unknown" not in result

    def test_empty_metadata(self):
        """Empty dict passes through as empty dict."""
        assert sanitize_metadata({}) == {}

    def test_none_metadata(self):
        """None is converted to empty dict."""
        assert sanitize_metadata(None) == {}

    def test_non_dict_metadata(self):
        """Non-dict input returns empty dict."""
        assert sanitize_metadata("not a dict") == {}
        assert sanitize_metadata([1, 2, 3]) == {}
        assert sanitize_metadata(42) == {}

    def test_complex_values_stripped(self):
        """Nested dicts and lists in metadata values are dropped."""
        metadata = {
            "status_code": 200,
            "model": {"nested": "dict"},  # complex type — dropped
            "deny_reason": ["a", "list"],  # complex type — dropped
        }
        result = sanitize_metadata(metadata)
        assert result == {"status_code": 200}

    def test_oversized_values_truncated(self):
        """String values exceeding MAX_METADATA_VALUE_LENGTH are truncated."""
        long_value = "x" * (MAX_METADATA_VALUE_LENGTH + 100)
        metadata = {"model": long_value}
        result = sanitize_metadata(metadata)
        assert len(result["model"]) < len(long_value)
        assert "…[truncated]" in result["model"]

    def test_normal_values_not_truncated(self):
        """Short string values are kept intact."""
        metadata = {"model": "gpt-4-turbo"}
        result = sanitize_metadata(metadata)
        assert result["model"] == "gpt-4-turbo"

    def test_allowlist_is_frozen(self):
        """The allowlist cannot be mutated at runtime."""
        with pytest.raises(AttributeError):
            ALLOWED_METADATA_KEYS.add("hacked")  # type: ignore[attr-defined]


# ── PII Field Rejection ────────────────────────────────────────────────


class TestPIIRejection:
    """Test that PII fields are blocked from the audit log."""

    @pytest.mark.parametrize(
        "field",
        [
            "email",
            "phone",
            "name",
            "authorization",
            "password",
            "ssn",
            "credit_card",
            "body",
            "request_body",
            "response_body",
            "headers",
            "request_headers",
            "response_headers",
            "cookie",
            "session_id",
            "access_token",
        ],
    )
    def test_pii_fields_blocked(self, field):
        """Known PII fields are rejected from metadata.

        NOTE: ``ip_address`` and ``user_agent`` were in this list before
        change-log v2.1. They are now allowlisted for SOC 2 CC7.2 /
        HIPAA §164.312(b) compliance — see ``test_ip_and_ua_allowlisted_for_compliance``
        below for the positive assertion.
        """
        metadata = {"status_code": 200, field: "sensitive-data"}
        result = sanitize_metadata(metadata)
        assert field not in result
        assert result == {"status_code": 200}

    def test_multiple_pii_fields_blocked(self):
        """All PII fields are blocked in a single pass."""
        metadata = {
            "status_code": 200,
            "email": "user@example.com",
            "phone": "555-1234",
            "client_ip": "192.168.1.1",  # aliases of ip_address stay blocked
            "body": '{"secret": "data"}',
        }
        result = sanitize_metadata(metadata)
        assert result == {"status_code": 200}

    def test_ip_and_ua_allowlisted_for_compliance(self):
        """change_log v2.1: ip_address + user_agent survive sanitization.

        SOC 2 CC7.2 and HIPAA §164.312(b) expect these on audit rows.
        Only the canonical spellings are allowlisted — aliases like
        ``client_ip`` / ``remote_addr`` / ``ua`` stay blocked so they
        can't sneak in under a variant name.
        """
        metadata = {
            "ip_address": "203.0.113.7",
            "user_agent": "ai-identity-sdk/1.0",
            "action_type": "agent_created",
            "resource_type": "agent",
        }
        result = sanitize_metadata(metadata)
        assert result["ip_address"] == "203.0.113.7"
        assert result["user_agent"] == "ai-identity-sdk/1.0"

    def test_is_pii_field_explicit_blocklist(self):
        """is_pii_field catches explicitly blocklisted names.

        ``ip_address`` was removed from the blocklist in change-log
        v2.1 (see sanitizer.py §Change-log v2.1 source context).
        The allowlist-wins rule in ``sanitize_metadata`` means any
        PII pattern match on an allowlisted key is overridden.
        """
        assert is_pii_field("email")
        assert is_pii_field("phone_number")
        assert is_pii_field("authorization")
        assert is_pii_field("body")
        assert is_pii_field("request_body")
        assert is_pii_field("headers")
        assert is_pii_field("cookie")
        assert is_pii_field("ssn")
        assert is_pii_field("credit_card")
        # Aliases of the canonical allowlisted spellings are still PII.
        assert is_pii_field("client_ip")
        assert is_pii_field("remote_addr")
        assert is_pii_field("x_forwarded_for")

    def test_is_pii_field_pattern_detection(self):
        """is_pii_field catches PII-like patterns not in the explicit list."""
        assert is_pii_field("user_email_addr")
        assert is_pii_field("phone_ext")
        assert is_pii_field("ip_address_v6")
        assert is_pii_field("auth_token_v2")
        assert is_pii_field("my_password_hash")
        assert is_pii_field("request_body_json")
        assert is_pii_field("response_header_raw")

    def test_is_pii_field_no_false_positives_on_metrics(self):
        """Legitimate metrics fields are NOT flagged as PII."""
        assert not is_pii_field("token_count")
        assert not is_pii_field("header_size")
        assert not is_pii_field("body_length")

    def test_is_pii_field_safe_names(self):
        """Legitimate metadata field names are not flagged as PII."""
        assert not is_pii_field("status_code")
        assert not is_pii_field("deny_reason")
        assert not is_pii_field("key_type")
        assert not is_pii_field("model")
        assert not is_pii_field("latency_ms")

    def test_pii_blocklist_is_frozen(self):
        """The PII blocklist cannot be mutated at runtime."""
        with pytest.raises(AttributeError):
            PII_FIELD_BLOCKLIST.add("hacked")  # type: ignore[attr-defined]

    def test_body_content_fields_comprehensively_blocked(self):
        """ALL body-related field names are blocked."""
        body_fields = [
            "body",
            "request_body",
            "response_body",
            "payload",
            "request_payload",
            "response_payload",
            "content",
            "request_content",
            "response_content",
            "data",
            "request_data",
            "response_data",
            "raw",
            "raw_request",
            "raw_response",
        ]
        for field in body_fields:
            assert is_pii_field(field), f"{field} should be PII-blocked"
            metadata = {field: "some content"}
            result = sanitize_metadata(metadata)
            assert field not in result, f"{field} should be stripped"


# ── No Bodies in Audit Log ──────────────────────────────────────────────


class TestNoBodyContent:
    """Verify that request/response bodies never reach the audit log."""

    def test_body_field_stripped_from_metadata(self):
        """Body content passed in metadata is stripped."""
        metadata = {
            "status_code": 200,
            "body": '{"messages": [{"role": "user", "content": "Hello"}]}',
            "response_body": '{"choices": [{"text": "Hi"}]}',
        }
        result = sanitize_metadata(metadata)
        assert "body" not in result
        assert "response_body" not in result

    def test_audit_entry_contains_no_body(self, db_session):
        """Audit entries created with body metadata don't store it."""
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={
                "status_code": 200,
                "body": "SECRET REQUEST BODY",
                "response_body": "SECRET RESPONSE BODY",
                "headers": {"Authorization": "Bearer secret-token"},
            },
        )
        # The stored metadata should only have status_code
        assert "body" not in entry.request_metadata
        assert "response_body" not in entry.request_metadata
        assert "headers" not in entry.request_metadata
        assert entry.request_metadata.get("status_code") == 200

    def test_audit_model_has_no_body_columns(self):
        """The AuditLog model does not have body columns."""
        from common.models.audit_log import AuditLog

        column_names = {c.name for c in AuditLog.__table__.columns}
        body_columns = {
            "request_body",
            "response_body",
            "body",
            "request_payload",
            "response_payload",
            "request_content",
            "response_content",
            "raw_request",
            "raw_response",
        }
        assert column_names.isdisjoint(body_columns), (
            f"AuditLog has body columns: {column_names & body_columns}"
        )


# ── PII Scan on Audit Entries ───────────────────────────────────────────


class TestPIIScan:
    """Verify that a PII scan of audit entries returns zero hits."""

    def test_pii_scan_clean_entries(self, db_session):
        """Create entries with PII in metadata and verify none persisted.

        ``ip_address`` and ``user_agent`` are intentionally excluded
        from this scan — they are allowlisted as of change-log v2.1
        for SOC 2 / HIPAA audit compliance. See
        ``TestPIIRejection::test_ip_and_ua_allowlisted_for_compliance``.
        """
        # Try to inject various PII into metadata
        pii_metadata = {
            "email": "user@example.com",
            "phone": "555-123-4567",
            "client_ip": "10.0.0.1",  # alias stays blocked
            "authorization": "Bearer eyJhbGci...",
            "cookie": "session=abc123",
            "body": '{"prompt": "confidential info"}',
            # These should survive:
            "status_code": 200,
            "key_type": "runtime",
        }

        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata=pii_metadata,
        )

        # Scan all fields for PII. Allowlisted compliance fields that
        # happen to match a PII pattern (ip_address matches ip_addr)
        # are OK by policy — is_pii_field is a name-based heuristic,
        # and the allowlist-wins rule is the authoritative gate.
        stored = entry.request_metadata
        for key in stored:
            if key in {"ip_address", "user_agent"}:
                continue
            assert not is_pii_field(key), f"PII field '{key}' found in audit entry"

        # Verify the clean fields survived
        assert stored.get("status_code") == 200
        assert stored.get("key_type") == "runtime"

    def test_pii_scan_multiple_entries(self, db_session):
        """Multiple entries are all clean of PII."""
        for i in range(5):
            create_audit_entry(
                db_session,
                agent_id=AGENT_ID,
                endpoint=f"/v1/endpoint-{i}",
                method="POST",
                decision="allow",
                request_metadata={
                    "email": f"user{i}@example.com",
                    "password": "secret",
                    "status_code": 200,
                },
            )

        from common.models import AuditLog

        entries = db_session.query(AuditLog).all()
        assert len(entries) == 5

        for entry in entries:
            for key in entry.request_metadata:
                assert not is_pii_field(key), f"PII field '{key}' in entry {entry.id}"


# ── PII Redaction (Debug Logging) ──────────────────────────────────────


class TestPIIRedaction:
    """Test PII redaction for the debug logger."""

    def test_redact_email(self):
        """Email addresses are redacted."""
        assert "[EMAIL_REDACTED]" in redact_pii("Contact user@example.com for help")

    def test_redact_phone(self):
        """Phone numbers are redacted."""
        assert "[PHONE_REDACTED]" in redact_pii("Call 555-123-4567")

    def test_redact_ssn(self):
        """SSN patterns are redacted."""
        assert "[SSN_REDACTED]" in redact_pii("SSN: 123-45-6789")

    def test_redact_ip_address(self):
        """IP addresses are redacted."""
        assert "[IP_REDACTED]" in redact_pii("Client IP: 192.168.1.100")

    def test_redact_api_key(self):
        """API keys are redacted."""
        result = redact_pii("Key: aid_sk_abc123def456")
        assert "aid_sk_[REDACTED]" in result
        assert "abc123" not in result

    def test_redact_admin_key(self):
        """Admin keys are redacted."""
        result = redact_pii("Key: aid_admin_xyz789secret")
        assert "aid_admin_[REDACTED]" in result
        assert "xyz789" not in result

    def test_redact_bearer_token(self):
        """Bearer tokens are redacted."""
        result = redact_pii("Authorization: Bearer eyJhbGciOiJIUzI1NiJ9.abc.def")
        assert "[REDACTED]" in result

    def test_redact_no_pii(self):
        """Strings without PII are returned unchanged."""
        clean = "Request to /v1/chat took 42ms"
        assert redact_pii(clean) == clean

    def test_redact_dict_nested(self):
        """Dict redaction works recursively."""
        data = {
            "endpoint": "/v1/chat",
            "user_info": "Contact user@example.com",
            "nested": {"ip": "From 10.0.0.1"},
        }
        result = redact_dict(data)
        assert result["endpoint"] == "/v1/chat"
        assert "[EMAIL_REDACTED]" in result["user_info"]
        assert "[IP_REDACTED]" in result["nested"]["ip"]

    def test_redact_empty_string(self):
        """Empty strings pass through."""
        assert redact_pii("") == ""

    def test_redact_none(self):
        """None passes through."""
        assert redact_pii(None) is None


# ── Sanitizer Integration with Writer ──────────────────────────────────


class TestSanitizerIntegration:
    """Verify the sanitizer is wired into create_audit_entry correctly."""

    def test_sanitizer_called_on_create(self, db_session):
        """create_audit_entry passes metadata through sanitize_metadata."""
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={
                "status_code": 200,
                "unknown_field": "dropped",
                "email": "pii@blocked.com",
            },
        )
        # Only allowed, non-PII fields survive
        assert entry.request_metadata == {"status_code": 200}

    def test_clean_metadata_passes_through(self, db_session):
        """Metadata with only allowed keys passes through unchanged."""
        metadata = {"deny_reason": "policy_denied", "status_code": 403, "key_type": "runtime"}
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/admin",
            method="POST",
            decision="deny",
            request_metadata=metadata,
        )
        assert entry.request_metadata == metadata

    def test_none_metadata_creates_empty_dict(self, db_session):
        """None metadata results in empty dict in the entry."""
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
        )
        assert entry.request_metadata == {}

    def test_hash_computed_on_sanitized_metadata(self, db_session):
        """The HMAC hash is computed AFTER sanitization, not before."""
        from datetime import UTC

        from common.audit.writer import compute_entry_hash

        # Create entry with PII that will be stripped
        entry = create_audit_entry(
            db_session,
            agent_id=AGENT_ID,
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            request_metadata={
                "status_code": 200,
                "email": "should-not-be-in-hash@example.com",
            },
        )

        # Recompute hash using the SANITIZED metadata (what's actually stored)
        created_at = entry.created_at
        if created_at.tzinfo is None:
            created_at = created_at.replace(tzinfo=UTC)

        recomputed = compute_entry_hash(
            agent_id=entry.agent_id,
            endpoint=entry.endpoint,
            method=entry.method,
            decision=entry.decision,
            cost_estimate_usd=(
                float(entry.cost_estimate_usd) if entry.cost_estimate_usd is not None else None
            ),
            latency_ms=entry.latency_ms,
            request_metadata=entry.request_metadata,  # sanitized
            created_at=created_at,
            prev_hash=entry.prev_hash,
        )
        assert recomputed == entry.entry_hash


# ── Debug Logging ──────────────────────────────────────────────────────


class TestDebugLogging:
    """Test opt-in debug logging behavior."""

    @patch("common.audit.debug_log.settings")
    def test_debug_logging_disabled_by_default(self, mock_settings):
        """Debug logging is a no-op when disabled."""
        mock_settings.audit_debug_logging = False

        from common.audit.debug_log import write_debug_entry

        # Should not raise
        write_debug_entry(
            agent_id="test",
            endpoint="/v1/chat",
            method="POST",
            decision="allow",
            raw_metadata={"email": "user@example.com"},
        )

    def test_redact_dict_with_empty(self):
        """Redacting an empty dict returns empty dict."""
        assert redact_dict({}) == {}

    def test_redact_dict_non_dict(self):
        """Redacting a non-dict returns empty dict."""
        assert redact_dict("not a dict") == {}
        assert redact_dict(None) == {}
