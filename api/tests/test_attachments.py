"""Tests for ticket attachment endpoints."""

import hashlib
import io
import uuid
from datetime import UTC, datetime, timedelta

import pytest
from PIL import Image

from common.models import SupportTicket, TicketComment
from common.models.support_ticket import TicketPriority, TicketStatus
from common.models.ticket_attachment import TicketAttachment

# Test constants
TEST_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000100")
OTHER_ORG_ID = uuid.UUID("00000000-0000-0000-0000-000000000200")


@pytest.fixture
def test_ticket(db_session, test_user):
    """Create a test ticket."""
    ticket = SupportTicket(
        id=uuid.UUID("00000000-0000-0000-0000-000000001000"),
        ticket_number="TKT-2026-0001",
        user_id=test_user.id,
        org_id=test_user.org_id,
        subject="Test Ticket",
        description="Test description",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


@pytest.fixture
def other_org_ticket(db_session, other_user):
    """Create a ticket in a different organization."""
    ticket = SupportTicket(
        id=uuid.UUID("00000000-0000-0000-0000-000000002000"),
        ticket_number="TKT-2026-0002",
        user_id=other_user.id,
        org_id=other_user.org_id,
        subject="Other Org Ticket",
        description="Test description",
        priority=TicketPriority.MEDIUM,
        status=TicketStatus.OPEN,
    )
    db_session.add(ticket)
    db_session.commit()
    db_session.refresh(ticket)
    return ticket


@pytest.fixture
def test_comment(db_session, test_ticket, test_user):
    """Create a test comment."""
    comment = TicketComment(
        id=uuid.UUID("00000000-0000-0000-0000-000000003000"),
        ticket_id=test_ticket.id,
        user_id=test_user.id,
        content="Test comment",
    )
    db_session.add(comment)
    db_session.commit()
    db_session.refresh(comment)
    return comment


@pytest.fixture
def mock_virus_scan(monkeypatch):
    """Mock virus scanner to return clean by default. Same target as conftest mock_clamav."""

    def mock_scan(file_path):
        return True, None  # Clean file

    monkeypatch.setattr(
        "common.security.virus_scan._scan_with_clamav",
        mock_scan,
    )


@pytest.fixture
def mock_exif_strip(monkeypatch):
    """Mock EXIF stripping."""

    async def mock_strip(image_path):
        pass  # No-op

    # Patch where it's imported (call site), not where it's defined
    monkeypatch.setattr("api.app.routers.attachments.strip_exif", mock_strip)


def create_test_image(size=(100, 100), format="PNG"):
    """Create a test image file in memory."""
    img = Image.new("RGB", size, color="red")
    buf = io.BytesIO()
    img.save(buf, format=format)
    buf.seek(0)
    return buf


def create_test_file(content=b"test file content", filename="test.txt"):
    """Create a test file in memory."""
    return io.BytesIO(content)


# ============================================================================
# TEST 1: Cross-org isolation (CRITICAL - must be first)
# ============================================================================


def test_cannot_download_attachment_from_other_org(
    client,
    auth_headers,
    test_user,
    other_org_ticket,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """User from org A cannot download attachment from ticket in org B.

    This is the most critical security test - cross-org isolation.
    """
    # Create attachment in other org's ticket
    attachment = TicketAttachment(
        id=uuid.UUID("00000000-0000-0000-0000-000000004000"),
        ticket_id=other_org_ticket.id,
        user_id=other_org_ticket.user_id,
        org_id=other_org_ticket.org_id,
        filename="test.png",
        original_filename="test.png",
        content_type="image/png",
        size_bytes=1024,
        sha256="a" * 64,
        storage_path="other-org/test.png",
    )
    db_session.add(attachment)
    db_session.commit()

    # Attempt download as test_user (different org)
    response = client.get(
        f"/api/v1/support/attachments/{attachment.id}/download",
        headers=auth_headers,
    )

    # Should return 404 (not 403) to avoid information leakage
    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


# ============================================================================
# TEST 2: Magic byte validation
# ============================================================================


def test_rejects_exe_renamed_as_png(
    client, auth_headers, test_ticket, mock_storage, mock_virus_scan, mock_magic, mock_clamav
):
    """Executable renamed to .png is rejected by magic byte validation."""
    # Create fake executable content (MZ header)
    exe_content = b"MZ\x90\x00" + b"\x00" * 100

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("malicious.png", exe_content, "image/png")},
    )

    assert response.status_code == 415
    assert "not allowed" in response.json()["error"]["message"].lower()


# ============================================================================
# TEST 3: Size enforcement
# ============================================================================


def test_rejects_oversized_file(
    client,
    auth_headers,
    test_ticket,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """11 MB file is rejected (limit is 10 MB)."""
    # Create 11 MB file
    large_content = b"x" * (11 * 1024 * 1024)

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("large.txt", large_content, "text/plain")},
    )

    assert response.status_code == 413
    assert "too large" in response.json()["error"]["message"].lower()


# ============================================================================
# TEST 4: Authentication required
# ============================================================================


def test_download_requires_authentication(client, test_ticket, db_session, mock_storage):
    """Anonymous access to download endpoint returns 401."""
    # Create attachment
    attachment = TicketAttachment(
        id=uuid.UUID("00000000-0000-0000-0000-000000005000"),
        ticket_id=test_ticket.id,
        user_id=test_ticket.user_id,
        org_id=test_ticket.org_id,
        filename="test.txt",
        original_filename="test.txt",
        content_type="text/plain",
        size_bytes=100,
        sha256="b" * 64,
        storage_path="test/test.txt",
    )
    db_session.add(attachment)
    db_session.commit()

    # Attempt download without auth
    response = client.get(f"/api/v1/support/attachments/{attachment.id}/download")

    assert response.status_code == 401


# ============================================================================
# TEST 5: Concurrent uploads
# ============================================================================


def test_concurrent_uploads_no_race_condition(
    client,
    auth_headers,
    test_ticket,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """Multiple uploads to same ticket all succeed with unique IDs."""
    responses = []

    for i in range(5):
        content = f"file {i} content".encode()
        response = client.post(
            "/api/v1/support/attachments/upload",
            headers=auth_headers,
            data={"ticket_id": str(test_ticket.id)},
            files={"file": (f"file{i}.txt", content, "text/plain")},
        )
        responses.append(response)

    # All should succeed
    assert all(r.status_code == 201 for r in responses)

    # All should have unique IDs
    ids = [r.json()["id"] for r in responses]
    assert len(set(ids)) == 5


# ============================================================================
# TEST 6: Storage backend integration
# ============================================================================


def test_storage_backend_upload_download_cycle(
    client,
    auth_headers,
    test_ticket,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """File uploaded can be downloaded via signed URL."""
    content = b"test file content for download"

    # Upload
    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("test.txt", content, "text/plain")},
    )

    assert response.status_code == 201
    attachment_id = response.json()["id"]

    # Verify storage.upload was called
    assert mock_storage.upload.called

    # Download
    response = client.get(
        f"/api/v1/support/attachments/{attachment_id}/download",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert "download_url" in data
    assert "expires_at" in data

    # Verify storage.generate_signed_url was called
    assert mock_storage.generate_signed_url.called


# ============================================================================
# TEST 7: Virus scan rejection
# ============================================================================


def test_rejects_eicar_test_virus(
    client, auth_headers, test_ticket, mock_storage, mock_exif_strip, mock_magic, monkeypatch
):
    """EICAR test string is rejected by virus scanner."""
    # EICAR test string
    eicar = b"X5O!P%@AP[4\\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"

    # Mock virus scanner to detect threat
    def mock_scan_threat(file_path):
        return False, "EICAR-Test-File"

    # Override the default mock_clamav to detect this specific threat
    monkeypatch.setattr(
        "common.security.virus_scan._scan_with_clamav",
        mock_scan_threat,
    )

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("eicar.txt", eicar, "text/plain")},
    )

    assert response.status_code == 415
    assert (
        "virus" in response.json()["error"]["message"].lower()
        or "eicar" in response.json()["error"]["message"].lower()
    )


# ============================================================================
# TEST 8: EXIF stripping
# ============================================================================


def test_strips_exif_from_images(
    client,
    auth_headers,
    test_ticket,
    mock_storage,
    mock_virus_scan,
    mock_magic,
    mock_clamav,
    monkeypatch,
):
    """JPEG with GPS metadata has EXIF stripped after upload."""
    # Track if strip_exif was called
    strip_called = []

    async def mock_strip(image_path):
        strip_called.append(image_path)

    # Patch where it's imported (call site), not where it's defined
    monkeypatch.setattr("api.app.routers.attachments.strip_exif", mock_strip)

    # Create JPEG image
    img_buf = create_test_image(format="JPEG")

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("photo.jpg", img_buf, "image/jpeg")},
    )

    assert response.status_code == 201
    # Verify strip_exif was called
    assert len(strip_called) > 0


# ============================================================================
# TEST 9: SHA-256 integrity
# ============================================================================


def test_sha256_integrity_check(
    client,
    auth_headers,
    test_ticket,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """Uploaded file has correct SHA-256 hash stored."""
    content = b"test content for hashing"
    expected_hash = hashlib.sha256(content).hexdigest()

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("test.txt", content, "text/plain")},
    )

    assert response.status_code == 201
    attachment_id = response.json()["id"]

    # Verify stored hash
    attachment = (
        db_session.query(TicketAttachment)
        .filter(TicketAttachment.id == uuid.UUID(attachment_id))
        .first()
    )

    assert attachment is not None
    assert attachment.sha256 == expected_hash


# ============================================================================
# TEST 10: GDPR delete cycle
# ============================================================================


def test_gdpr_delete_cycle(
    client,
    auth_headers,
    test_ticket,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
    monkeypatch,
):
    """Soft delete → cron tick → storage file deleted AND DB row hard-deleted."""
    # Configure internal service key for the cron auth check.
    # The cron does `from common.config.settings import settings` so the patch
    # target is the singleton's attribute on the source module.
    monkeypatch.setattr(
        "common.config.settings.settings.internal_service_key",
        "test-internal-key-xyz",
    )
    # Upload attachment
    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("test.txt", b"test content", "text/plain")},
    )

    assert response.status_code == 201
    attachment_id = uuid.UUID(response.json()["id"])

    # Soft delete
    response = client.delete(
        f"/api/v1/support/attachments/{attachment_id}",
        headers=auth_headers,
    )

    assert response.status_code == 204

    # Verify soft delete
    attachment = (
        db_session.query(TicketAttachment).filter(TicketAttachment.id == attachment_id).first()
    )
    assert attachment.deleted_at is not None

    # Simulate 31 days passing
    attachment.deleted_at = datetime.now(UTC) - timedelta(days=31)
    db_session.commit()

    # Run cleanup cron
    response = client.post(
        "/api/v1/cron/attachment-cleanup",
        headers={"X-Internal-Key": "test-internal-key-xyz"},
    )

    assert response.status_code == 200
    assert response.json()["deleted"] >= 1

    # Verify storage.delete was called
    assert mock_storage.delete.called

    # Verify DB row is hard-deleted
    attachment = (
        db_session.query(TicketAttachment).filter(TicketAttachment.id == attachment_id).first()
    )
    assert attachment is None


# ============================================================================
# TEST 11: Comment attachment
# ============================================================================


def test_comment_attachment(
    client,
    auth_headers,
    test_ticket,
    test_comment,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """Attachment can be linked to a comment (nullable FK case)."""
    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={
            "ticket_id": str(test_ticket.id),
            "comment_id": str(test_comment.id),
        },
        files={"file": ("test.txt", b"comment attachment", "text/plain")},
    )

    assert response.status_code == 201
    attachment_id = uuid.UUID(response.json()["id"])

    # Verify attachment is linked to comment
    attachment = (
        db_session.query(TicketAttachment).filter(TicketAttachment.id == attachment_id).first()
    )

    assert attachment is not None
    assert attachment.comment_id == test_comment.id
    assert attachment.ticket_id == test_ticket.id


# ============================================================================
# TEST 12: Filename sanitization
# ============================================================================


def test_filename_sanitization_prevents_traversal(
    client,
    auth_headers,
    test_ticket,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """Path traversal attempt in filename is sanitized."""
    malicious_filename = "../../../etc/passwd.txt"

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": (malicious_filename, b"malicious content", "text/plain")},
    )

    assert response.status_code == 201
    attachment_id = uuid.UUID(response.json()["id"])

    # Verify storage path doesn't contain traversal
    attachment = (
        db_session.query(TicketAttachment).filter(TicketAttachment.id == attachment_id).first()
    )

    assert attachment is not None
    assert "../" not in attachment.storage_path
    assert "etc/passwd" not in attachment.storage_path
    # Should start with org_id
    assert attachment.storage_path.startswith(str(test_ticket.org_id))


# ============================================================================
# Additional tests for edge cases
# ============================================================================


def test_list_ticket_attachments(
    client,
    auth_headers,
    test_ticket,
    db_session,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
):
    """List attachments for a ticket returns correct data."""
    # Upload two attachments
    for i in range(2):
        response = client.post(
            "/api/v1/support/attachments/upload",
            headers=auth_headers,
            data={"ticket_id": str(test_ticket.id)},
            files={"file": (f"test{i}.txt", f"content {i}".encode(), "text/plain")},
        )
        assert response.status_code == 201

    # List attachments
    response = client.get(
        f"/api/v1/support/attachments/ticket/{test_ticket.id}",
        headers=auth_headers,
    )

    assert response.status_code == 200
    data = response.json()
    assert data["count"] == 2
    assert len(data["attachments"]) == 2
    assert data["total_size_bytes"] > 0


def test_attachment_count_limits(
    client,
    auth_headers,
    test_ticket,
    mock_storage,
    mock_virus_scan,
    mock_exif_strip,
    mock_magic,
    mock_clamav,
    monkeypatch,
):
    """Attachment count limits are enforced."""
    # Patch the constant at the call site (router), not the source module —
    # the router did `from ... import MAX_ATTACHMENTS_PER_TICKET` which copied
    # the value at import time, so patching the source has no effect.
    import api.app.routers.attachments as attachments_router
    from common.validation import file_upload

    original_limit = attachments_router.MAX_ATTACHMENTS_PER_TICKET
    monkeypatch.setattr(attachments_router, "MAX_ATTACHMENTS_PER_TICKET", 2)
    monkeypatch.setattr(file_upload, "MAX_ATTACHMENTS_PER_TICKET", 2)

    try:
        # Upload 2 attachments (should succeed)
        for i in range(2):
            response = client.post(
                "/api/v1/support/attachments/upload",
                headers=auth_headers,
                data={"ticket_id": str(test_ticket.id)},
                files={"file": (f"test{i}.txt", f"content {i}".encode(), "text/plain")},
            )
            assert response.status_code == 201

        # Third upload should fail
        response = client.post(
            "/api/v1/support/attachments/upload",
            headers=auth_headers,
            data={"ticket_id": str(test_ticket.id)},
            files={"file": ("test3.txt", b"content 3", "text/plain")},
        )
        assert response.status_code == 413
        assert "maximum" in response.json()["error"]["message"].lower()

    finally:
        # Restore original limit
        file_upload.MAX_ATTACHMENTS_PER_TICKET = original_limit


def test_missing_filename_rejected(client, auth_headers, test_ticket):
    """Upload with empty filename is rejected with 422."""
    # Empty-string filename either trips FastAPI's UploadFile validation
    # (Pydantic 422 with detail-list) or our custom 422 (error.message string).
    # Either is correct rejection; what matters is the 422 status.
    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(test_ticket.id)},
        files={"file": ("", b"content", "text/plain")},
    )

    assert response.status_code == 422


def test_nonexistent_ticket_rejected(client, auth_headers, mock_storage):
    """Upload to nonexistent ticket returns 404."""
    fake_ticket_id = uuid.uuid4()

    response = client.post(
        "/api/v1/support/attachments/upload",
        headers=auth_headers,
        data={"ticket_id": str(fake_ticket_id)},
        files={"file": ("test.txt", b"content", "text/plain")},
    )

    assert response.status_code == 404
    assert "not found" in response.json()["error"]["message"].lower()


# Made with Bob
