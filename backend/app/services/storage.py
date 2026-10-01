"""File storage abstraction.

Default backend is the local filesystem (``localdata/``). The interface is
deliberately small so an S3/MinIO backend can be added later without touching
routers.
"""

from __future__ import annotations

import functools
import uuid
from pathlib import Path

import anyio.to_thread

from app.core.config import get_settings


class LocalStorage:
    def __init__(self, base_path: str) -> None:
        self.base = Path(base_path)
        self.base.mkdir(parents=True, exist_ok=True)

    def _path(self, key: str) -> Path:
        path = (self.base / key).resolve()
        if not str(path).startswith(str(self.base.resolve())):
            raise ValueError("Invalid storage key")
        return path

    def save(self, data: bytes, *, filename: str, prefix: str) -> str:
        safe_name = Path(filename).name or "file"
        key = f"{prefix}/{uuid.uuid4().hex}_{safe_name}"
        path = self._path(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return key

    def read(self, key: str) -> bytes:
        return self._path(key).read_bytes()

    async def save_async(self, data: bytes, *, filename: str, prefix: str) -> str:
        return await anyio.to_thread.run_sync(
            functools.partial(self.save, data, filename=filename, prefix=prefix)
        )

    async def read_async(self, key: str) -> bytes:
        return await anyio.to_thread.run_sync(self.read, key)


_storage: LocalStorage | None = None


def get_storage() -> LocalStorage:
    global _storage
    if _storage is None:
        _storage = LocalStorage(get_settings().local_storage_path)
    return _storage
