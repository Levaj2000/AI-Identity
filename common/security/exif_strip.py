"""EXIF metadata stripping for images to prevent PII leaks."""

import logging
from pathlib import Path

from PIL import Image

logger = logging.getLogger("ai_identity.security.exif_strip")


async def strip_exif(image_path: Path) -> None:
    """Remove EXIF metadata from image files.

    EXIF data can contain sensitive information:
    - GPS coordinates
    - Camera serial numbers
    - Timestamps
    - Software versions
    - Internal network information

    Args:
        image_path: Path to image file to strip

    Raises:
        IOError: If image cannot be processed
    """
    # Only process image files
    extension = image_path.suffix.lower()
    if extension not in [".jpg", ".jpeg", ".png", ".webp"]:
        return

    try:
        # Open image
        img = Image.open(image_path)

        # Get image data without EXIF
        # For JPEG, we can explicitly strip EXIF by saving without it
        if extension in [".jpg", ".jpeg"]:
            # Save without EXIF data
            img.save(image_path, "JPEG", exif=b"", quality=95)
        elif extension == ".png":
            # PNG stores metadata differently - save without it
            img.save(image_path, "PNG", optimize=True)
        elif extension == ".webp":
            # WebP can also contain EXIF
            img.save(image_path, "WEBP", exif=b"", quality=95)

        logger.info("Stripped EXIF metadata from %s", image_path)

    except Exception as e:
        logger.error("Failed to strip EXIF from %s: %s", image_path, str(e))
        raise OSError(f"Failed to process image: {str(e)}") from e


# Made with Bob
