"""Storage backend abstraction for file storage operations.

This module provides a unified interface for file storage that can be backed by
local disk (dev/test) or Google Cloud Storage (production). Used by both
compliance exports and ticket attachments.
"""

from common.storage.backend import StorageBackend
from common.storage.factory import get_storage_backend
from common.storage.local_backend import LocalStorageBackend

__all__ = ["StorageBackend", "LocalStorageBackend", "get_storage_backend"]

# GCS backend is imported conditionally to avoid requiring gcloud-aio-storage
# in environments where it's not needed
try:
    from common.storage.gcs_backend import GCSStorageBackend

    __all__.append("GCSStorageBackend")
except ImportError:
    GCSStorageBackend = None

# Made with Bob
