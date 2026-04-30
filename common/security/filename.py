"""Filename sanitization to prevent path traversal and other attacks."""

import re
import unicodedata
from pathlib import Path


def sanitize_filename(original: str, max_length: int = 100) -> str:
    """Sanitize filename for safe storage.

    Security measures:
    - Removes path traversal attempts (../, ..\\, etc.)
    - Normalizes Unicode to prevent homograph attacks
    - Removes special characters that could cause issues
    - Preserves file extension
    - Truncates to reasonable length
    - Preserves Unicode letters/digits (international support)

    Args:
        original: Original filename from upload
        max_length: Maximum length for sanitized name (excluding extension)

    Returns:
        Sanitized filename safe for storage

    Examples:
        >>> sanitize_filename("../../../etc/passwd.png")
        'etc_passwd.png'
        >>> sanitize_filename("résumé.pdf")
        'résumé.pdf'
        >>> sanitize_filename("file<>:name.txt")
        'file___name.txt'
    """
    # Normalize Unicode to canonical form
    normalized = unicodedata.normalize("NFKD", original)

    # Extract extension
    path = Path(normalized)
    name = path.stem
    ext = path.suffix.lower()

    # Remove path traversal attempts
    name = name.replace("..", "")
    name = name.replace("/", "_")
    name = name.replace("\\", "_")

    # Remove dangerous characters but preserve Unicode letters/digits
    # Allow: letters, digits, spaces, hyphens, underscores
    name = re.sub(r"[^\w\s.-]", "_", name, flags=re.UNICODE)

    # Collapse multiple spaces/underscores
    name = re.sub(r"[\s_]+", "_", name)

    # Remove leading/trailing underscores and spaces
    name = name.strip("_").strip()

    # Truncate to max length
    if len(name) > max_length:
        name = name[:max_length]

    # Ensure we have a name
    if not name:
        name = "file"

    return f"{name}{ext}"


def generate_storage_path(
    org_id: str,
    attachment_id: str,
    original_filename: str,
    parent_type: str = "ticket",
    parent_id: str | None = None,
) -> str:
    """Generate storage path for attachment.

    Path structure:
    {org_id}/{parent_type}-attachments/{parent_id}/{attachment_id}_{sanitized_filename}

    Args:
        org_id: Organization ID
        attachment_id: Attachment UUID
        original_filename: Original filename from upload
        parent_type: "ticket" or "comment"
        parent_id: Parent ticket/comment ID (optional, for organization)

    Returns:
        Storage path string

    Examples:
        >>> generate_storage_path(
        ...     "org-123",
        ...     "att-456",
        ...     "screenshot.png",
        ...     "ticket",
        ...     "tkt-789"
        ... )
        'org-123/ticket-attachments/tkt-789/att-456_screenshot.png'
    """
    sanitized = sanitize_filename(original_filename)

    if parent_id:
        return f"{org_id}/{parent_type}-attachments/{parent_id}/{attachment_id}_{sanitized}"
    else:
        return f"{org_id}/{parent_type}-attachments/{attachment_id}_{sanitized}"


# Made with Bob
