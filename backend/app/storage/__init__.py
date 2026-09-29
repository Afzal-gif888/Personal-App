"""Blob storage for uploaded documents. `get_storage()` returns the configured backend."""

import hashlib
import os
import shutil
import tempfile
from abc import ABC, abstractmethod
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import BinaryIO

from app.core.config import get_settings
from app.core.errors import AppError

CHUNK = 1024 * 1024


class PayloadTooLarge(AppError):
    """File is too large"""

    status_code = 413
    code = "PAYLOAD_TOO_LARGE"


@dataclass
class StoredObject:
    key: str
    size: int
    sha256: str


class StorageBackend(ABC):
    @abstractmethod
    def save(self, key: str, stream: BinaryIO, *, max_bytes: int) -> StoredObject: ...

    @abstractmethod
    def path(self, key: str) -> Path:
        """Local path for streaming a download. Remote backends would return signed URLs instead."""

    @abstractmethod
    def delete(self, key: str) -> None: ...


class LocalStorage(StorageBackend):
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def path(self, key: str) -> Path:
        target = (self.root / key).resolve()
        if not target.is_relative_to(self.root):
            raise ValueError("Storage key escapes the storage root")
        return target

    def save(self, key: str, stream: BinaryIO, *, max_bytes: int) -> StoredObject:
        target = self.path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        digest, size = hashlib.sha256(), 0
        # Write to a temp file first so a rejected or interrupted upload never leaves a partial blob.
        fd, tmp = tempfile.mkstemp(dir=target.parent, suffix=".part")
        try:
            with os.fdopen(fd, "wb") as out:
                while chunk := stream.read(CHUNK):
                    size += len(chunk)
                    if size > max_bytes:
                        raise PayloadTooLarge(f"File exceeds the {max_bytes // (1024 * 1024)} MB limit")
                    digest.update(chunk)
                    out.write(chunk)
            shutil.move(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise
        return StoredObject(key=key, size=size, sha256=digest.hexdigest())

    def delete(self, key: str) -> None:
        self.path(key).unlink(missing_ok=True)


@lru_cache
def get_storage() -> StorageBackend:
    return LocalStorage(get_settings().storage_path)
