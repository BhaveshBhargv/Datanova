"""Storage abstraction for dataset artifacts.

Phase 2 ships a local-filesystem backend. The interface is deliberately small
so an S3/object-storage backend can drop in later without touching callers.
Relative paths are stored in the database; the backend resolves them.
"""
from __future__ import annotations

from pathlib import Path
from typing import Protocol

from app.core.config import settings


class Storage(Protocol):
    def write(self, rel_path: str, data: bytes) -> None: ...
    def read(self, rel_path: str) -> bytes: ...
    def delete(self, rel_path: str) -> None: ...
    def abspath(self, rel_path: str) -> str: ...


class LocalStorage:
    """Stores files under a base directory on the local filesystem."""

    def __init__(self, base_dir: str) -> None:
        self.base = Path(base_dir).resolve()
        self.base.mkdir(parents=True, exist_ok=True)

    def _full(self, rel_path: str) -> Path:
        # Resolve and ensure the path stays within the base directory.
        full = (self.base / rel_path).resolve()
        if not full.is_relative_to(self.base):
            raise ValueError("Resolved path escapes the storage root.")
        return full

    def write(self, rel_path: str, data: bytes) -> None:
        full = self._full(rel_path)
        full.parent.mkdir(parents=True, exist_ok=True)
        full.write_bytes(data)

    def read(self, rel_path: str) -> bytes:
        return self._full(rel_path).read_bytes()

    def delete(self, rel_path: str) -> None:
        full = self._full(rel_path)
        full.unlink(missing_ok=True)

    def abspath(self, rel_path: str) -> str:
        return str(self._full(rel_path))


storage: Storage = LocalStorage(settings.UPLOAD_DIR)
