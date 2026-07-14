"""
Storage backend factory.

Every caller gets a backend through `get_storage_backend()` rather than
constructing `LocalStorageBackend` directly. This is the one seam where
production would swap in S3 -- add a `settings.STORAGE_BACKEND` value
("local" | "s3"), branch here, and nothing else in the codebase changes.
"""

from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    """Returns the configured storage backend (currently always local)."""
    return LocalStorageBackend(base_dir=Path(settings.UPLOAD_DIR))


__all__ = ["StorageBackend", "LocalStorageBackend", "get_storage_backend"]
