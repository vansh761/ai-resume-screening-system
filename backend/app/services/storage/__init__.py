"""Storage backend factory."""

from functools import lru_cache
from pathlib import Path

from app.core.config import settings
from app.services.storage.base import StorageBackend
from app.services.storage.local import LocalStorageBackend


@lru_cache
def get_storage_backend() -> StorageBackend:
    return LocalStorageBackend(base_dir=Path(settings.UPLOAD_DIR))


__all__ = ["StorageBackend", "LocalStorageBackend", "get_storage_backend"]
