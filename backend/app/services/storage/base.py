"""
Storage backend abstraction.

Design decision
----------------
The rest of the codebase (the resume upload service, and eventually
report exports) depends on this interface, never on "the filesystem"
or "S3" directly. This is the same Dependency Inversion pattern used
for the database layer: swapping `LocalStorageBackend` for a future
`S3StorageBackend` should mean changing exactly one line — the factory
in `__init__.py` — and nothing in `resume_service.py` or any API
endpoint needs to know or care.
"""

from abc import ABC, abstractmethod


class StorageBackend(ABC):
    """Interface every storage implementation must satisfy."""

    @abstractmethod
    def save(self, file_bytes: bytes, storage_key: str) -> str:
        """
        Persists `file_bytes` under `storage_key` and returns the key
        actually used (implementations may need to sanitize/prefix it).
        """
        raise NotImplementedError

    @abstractmethod
    def read(self, storage_key: str) -> bytes:
        """Reads back the raw bytes stored under `storage_key`."""
        raise NotImplementedError

    @abstractmethod
    def delete(self, storage_key: str) -> None:
        """Removes the file at `storage_key`. No-op if it doesn't exist."""
        raise NotImplementedError

    @abstractmethod
    def exists(self, storage_key: str) -> bool:
        """Checks whether something is stored at `storage_key`."""
        raise NotImplementedError
