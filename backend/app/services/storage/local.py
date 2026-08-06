"""Local filesystem storage backend."""

from pathlib import Path

from app.services.storage.base import StorageBackend


class LocalStorageBackend(StorageBackend):
    def __init__(self, base_dir: Path) -> None:
        self.base_dir = base_dir
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _resolve(self, storage_key: str) -> Path:
        resolved = (self.base_dir / storage_key).resolve()
        if not str(resolved).startswith(str(self.base_dir.resolve())):
            raise ValueError(f"Invalid storage key (path traversal attempt): {storage_key}")
        return resolved

    def save(self, file_bytes: bytes, storage_key: str) -> str:
        path = self._resolve(storage_key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(file_bytes)
        return storage_key

    def read(self, storage_key: str) -> bytes:
        path = self._resolve(storage_key)
        if not path.exists():
            raise FileNotFoundError(f"No file stored at key: {storage_key}")
        return path.read_bytes()

    def delete(self, storage_key: str) -> None:
        path = self._resolve(storage_key)
        path.unlink(missing_ok=True)

    def exists(self, storage_key: str) -> bool:
        return self._resolve(storage_key).exists()
