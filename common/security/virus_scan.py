"""Virus scanning using ClamAV."""

import logging
from pathlib import Path

logger = logging.getLogger("ai_identity.security.virus_scan")

# Module-level lazy import with sentinel
try:
    import clamd as _clamd_module
except ImportError:
    _clamd_module = None


def _scan_with_clamav(file_path: Path) -> tuple[bool, str | None]:
    """Scan file with ClamAV daemon. Returns (is_clean, threat_name).

    Module-level seam so tests can monkeypatch it without needing
    ClamAV daemon running.

    Returns:
        - (True, None) if file is clean
        - (False, threat_name) if threat detected
        - (False, error_message) if scanner unavailable
    """
    if _clamd_module is None:
        logger.error("clamd not installed - cannot scan files")
        return False, "Virus scanner not available (clamd not installed)"

    try:
        # Connect to ClamAV daemon via Unix socket
        cd = _clamd_module.ClamdUnixSocket()

        # Scan the file
        result = cd.scan(str(file_path))

        if result is None:
            # No threats found
            return True, None

        # result format: {'/path/to/file': ('FOUND', 'Threat.Name')}
        file_result = result.get(str(file_path))

        if file_result is None:
            return True, None

        status, threat = file_result

        if status == "OK":
            return True, None
        else:
            logger.warning("Virus detected in %s: %s", file_path, threat)
            return False, threat

    except _clamd_module.ConnectionError as e:
        logger.error("ClamAV connection error: %s", str(e))
        return False, f"Virus scanner unavailable: {str(e)}"
    except Exception as e:
        logger.error("Virus scan error for %s: %s", file_path, str(e))
        return False, f"Scan error: {str(e)}"


async def scan_file(file_path: Path) -> tuple[bool, str | None]:
    """Scan file for viruses using ClamAV.

    Args:
        file_path: Path to file to scan

    Returns:
        Tuple of (is_clean, threat_name)
        - On clean file: (True, None)
        - On threat found: (False, threat_name)
        - On scanner error: (False, error_message)

    Note:
        Fails closed - if scanner is unavailable, returns (False, error).
        This ensures we never accept uploads when scanning is down.
    """
    return _scan_with_clamav(file_path)


# Made with Bob
