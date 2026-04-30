"""File upload validation - content type and security checks."""

import logging
from pathlib import Path

logger = logging.getLogger("ai_identity.validation.file_upload")

# Module-level lazy import with sentinel
try:
    import magic as _magic_module
except ImportError:
    _magic_module = None

# Allowed content types and their valid extensions
ALLOWED_CONTENT_TYPES = {
    # Images
    "image/png": [".png"],
    "image/jpeg": [".jpg", ".jpeg"],
    "image/gif": [".gif"],
    "image/webp": [".webp"],
    # Documents
    "application/pdf": [".pdf"],
    "text/plain": [".txt", ".log"],
    "text/markdown": [".md"],
    # Archives (with extra scrutiny)
    "application/zip": [".zip"],
}

# Maximum file sizes
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
MAX_TOTAL_SIZE_PER_TICKET = 100 * 1024 * 1024  # 100 MB
MAX_ATTACHMENTS_PER_TICKET = 20
MAX_ATTACHMENTS_PER_COMMENT = 10


def _detect_content_type(file_path: Path) -> str | None:
    """Detect content type via libmagic. Returns None if libmagic is unavailable.

    Module-level seam so tests can monkeypatch it without needing
    libmagic installed at the OS level.
    """
    if _magic_module is None:
        logger.error("python-magic not installed - cannot detect content types")
        return None

    try:
        mime = _magic_module.Magic(mime=True)
        return mime.from_file(str(file_path))
    except Exception as e:
        logger.error("Failed to detect content type for %s: %s", file_path, str(e))
        return None


async def validate_file_upload(
    file_path: Path,
    claimed_content_type: str | None = None,
    max_size_bytes: int = MAX_FILE_SIZE_BYTES,
) -> tuple[str | None, str | None]:
    """Validate uploaded file using magic bytes.

    Performs security checks:
    1. File size validation
    2. Magic byte content type detection
    3. Extension validation against detected type
    4. Claimed type validation (if provided)

    Args:
        file_path: Path to uploaded file
        claimed_content_type: Content-Type from upload (optional)
        max_size_bytes: Maximum allowed file size

    Returns:
        Tuple of (actual_content_type, error_message)
        - On success: (content_type, None)
        - On failure: (None, error_message)
    """
    # Check file exists
    if not file_path.exists():
        return None, f"File not found: {file_path}"

    # Size check
    size = file_path.stat().st_size
    if size > max_size_bytes:
        return None, f"File too large: {size} bytes (max {max_size_bytes})"

    if size == 0:
        return None, "File is empty"

    # Detect actual content type using magic bytes
    actual_content_type = _detect_content_type(file_path)
    if actual_content_type is None:
        return None, "Content type detection unavailable"

    # Validate content type is allowed
    if actual_content_type not in ALLOWED_CONTENT_TYPES:
        return None, f"File type not allowed: {actual_content_type}"

    # Validate file extension matches content type
    extension = file_path.suffix.lower()
    allowed_extensions = ALLOWED_CONTENT_TYPES[actual_content_type]

    if extension not in allowed_extensions:
        return (
            None,
            f"Extension {extension} not allowed for {actual_content_type}. "
            f"Allowed: {', '.join(allowed_extensions)}",
        )

    # If claimed content type provided, verify it matches actual
    if claimed_content_type and claimed_content_type != actual_content_type:
        return (
            None,
            f"Claimed content type {claimed_content_type} does not match "
            f"actual type {actual_content_type}",
        )

    return actual_content_type, None


def is_image(content_type: str) -> bool:
    """Check if content type is an image."""
    return content_type.startswith("image/")


# Made with Bob
