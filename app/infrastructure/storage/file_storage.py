"""Local and S3-compatible private object storage adapters."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from functools import partial
import os
from pathlib import Path
from typing import Protocol

from app.config.file_storage import FileStorageSettings
from app.core.exceptions import FileStorageError

_FILE_STORAGE_EXECUTOR = ThreadPoolExecutor(max_workers=4, thread_name_prefix="lms-file-storage")


class _StorageAdapter(Protocol):
    async def put(self, key: str, content: bytes, content_type: str) -> None: ...
    async def get(self, key: str) -> bytes: ...
    async def delete(self, key: str) -> None: ...


class LocalFileStorage:
    def __init__(self, root: str | Path):
        self.root = Path(root).expanduser().resolve()

    def _path(self, key: str) -> Path:
        if not key or "/" in key or "\\" in key or key in {".", ".."}:
            raise FileStorageError("invalid private storage key")
        return self.root / key[:2] / key

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        del content_type
        path = self._path(key)
        try:
            path.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(descriptor, "wb") as output:
                output.write(content)
        except OSError as exc:
            raise FileStorageError("file could not be stored") from exc

    async def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            return path.read_bytes()
        except OSError as exc:
            raise FileStorageError("file could not be retrieved") from exc

    async def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink(missing_ok=True)
        except OSError as exc:
            raise FileStorageError("file could not be removed") from exc


class S3CompatibleFileStorage:
    def __init__(self, settings: FileStorageSettings):
        if not settings.bucket:
            raise FileStorageError("S3-compatible storage bucket is not configured")
        self.settings = settings
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                import boto3
                from botocore.config import Config
            except ImportError as exc:
                raise FileStorageError("S3-compatible storage support is unavailable") from exc
            self._client = boto3.client(
                "s3",
                endpoint_url=self.settings.endpoint_url,
                region_name=self.settings.region,
                aws_access_key_id=self.settings.access_key_id.get_secret_value() if self.settings.access_key_id else None,
                aws_secret_access_key=self.settings.secret_access_key.get_secret_value() if self.settings.secret_access_key else None,
                config=Config(connect_timeout=5, read_timeout=30, retries={"max_attempts": 3}),
            )
        return self._client

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        try:
            await asyncio.get_running_loop().run_in_executor(_FILE_STORAGE_EXECUTOR, partial(self._get_client().put_object, Bucket=self.settings.bucket, Key=key, Body=content, ContentType=content_type))
        except Exception as exc:
            raise FileStorageError("file could not be stored") from exc

    async def get(self, key: str) -> bytes:
        try:
            response = await asyncio.get_running_loop().run_in_executor(_FILE_STORAGE_EXECUTOR, partial(self._get_client().get_object, Bucket=self.settings.bucket, Key=key))
            body = response["Body"]
            try:
                return await asyncio.get_running_loop().run_in_executor(_FILE_STORAGE_EXECUTOR, body.read)
            finally:
                await asyncio.get_running_loop().run_in_executor(_FILE_STORAGE_EXECUTOR, body.close)
        except Exception as exc:
            raise FileStorageError("file could not be retrieved") from exc

    async def delete(self, key: str) -> None:
        try:
            await asyncio.get_running_loop().run_in_executor(_FILE_STORAGE_EXECUTOR, partial(self._get_client().delete_object, Bucket=self.settings.bucket, Key=key))
        except Exception as exc:
            raise FileStorageError("file could not be removed") from exc


class ConfiguredFileStorage:
    """Routes writes to the configured backend and reads by persisted backend name."""

    def __init__(self, settings: FileStorageSettings):
        self.active_backend = settings.backend
        self._local = LocalFileStorage(settings.local_root)
        self._settings = settings
        self._s3: S3CompatibleFileStorage | None = None

    def _adapter(self, backend: str) -> _StorageAdapter:
        if backend == "local":
            return self._local
        if backend == "s3":
            if self._s3 is None:
                self._s3 = S3CompatibleFileStorage(self._settings)
            return self._s3
        raise FileStorageError("unsupported file storage backend")

    async def put(self, key: str, content: bytes, content_type: str) -> None:
        await self._adapter(self.active_backend).put(key, content, content_type)

    async def get(self, backend: str, key: str) -> bytes:
        return await self._adapter(backend).get(key)

    async def delete(self, backend: str, key: str) -> None:
        await self._adapter(backend).delete(key)
