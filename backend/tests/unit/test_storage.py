"""Unit tests for LocalStorageBackend — uses pytest's tmp_path for isolation."""

from pathlib import Path

import pytest

from app.services.storage.local import LocalStorageBackend


@pytest.mark.unit
def test_save_and_read_round_trip(tmp_path: Path) -> None:
    backend = LocalStorageBackend(base_dir=tmp_path)
    backend.save(b"hello resume content", "candidate-1/resume.pdf")

    assert backend.exists("candidate-1/resume.pdf") is True
    assert backend.read("candidate-1/resume.pdf") == b"hello resume content"


@pytest.mark.unit
def test_read_missing_file_raises(tmp_path: Path) -> None:
    backend = LocalStorageBackend(base_dir=tmp_path)
    with pytest.raises(FileNotFoundError):
        backend.read("does/not/exist.pdf")


@pytest.mark.unit
def test_delete_removes_file(tmp_path: Path) -> None:
    backend = LocalStorageBackend(base_dir=tmp_path)
    backend.save(b"content", "to-delete.pdf")
    assert backend.exists("to-delete.pdf") is True

    backend.delete("to-delete.pdf")
    assert backend.exists("to-delete.pdf") is False


@pytest.mark.unit
def test_path_traversal_is_rejected(tmp_path: Path) -> None:
    """A malicious storage key trying to escape base_dir must be rejected."""
    backend = LocalStorageBackend(base_dir=tmp_path)
    with pytest.raises(ValueError):
        backend.save(b"malicious", "../../etc/passwd")
