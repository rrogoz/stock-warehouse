"""Object storage behind one interface, local folder or S3-compatible (ADR-003, SW-16).

`from_config` is the only place that picks the backend, from `SW_STORAGE_BACKEND`; nothing
else in the engine knows which one it talks to.

Bucket layout. All keys are strings with `/` separators:

    warehouse/current.json                           pointer: {"version": 1, "database": "<key>"}
    warehouse/sw_<YYYYMMDDTHHMMSSZ>_<run_id>.duckdb  one per published run; names sort by date
    ops/run_log/<run_id>/started.json                written when the run starts
    ops/run_log/<run_id>/ended.json                  written when it ends: status, step counts

A run writes the pointer last, so an interruption before it leaves the old version current.
Bronze keys arrive with the connector stories.
"""

from __future__ import annotations

import os
import tempfile
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Any, Protocol

if TYPE_CHECKING:
    from mypy_boto3_s3 import S3Client


class ConfigError(Exception):
    """A missing or invalid setting; the command exits 2."""


class ObjectNotFoundError(KeyError):
    """The key does not exist in the storage."""


@dataclass(frozen=True)
class Config:
    backend: str
    root: str
    endpoint: str
    bucket: str
    access_key_id: str
    secret_access_key: str
    image_tag: str

    @classmethod
    def from_env(cls, env: Mapping[str, str]) -> Config:
        backend = env.get("SW_STORAGE_BACKEND", "")
        if backend not in ("local", "s3"):
            raise ConfigError("SW_STORAGE_BACKEND must be 'local' or 's3'")
        values = {
            "endpoint": env.get("SW_STORAGE_ENDPOINT", ""),
            "bucket": env.get("SW_STORAGE_BUCKET", ""),
            "access_key_id": env.get("SW_STORAGE_ACCESS_KEY_ID", ""),
            "secret_access_key": env.get("SW_STORAGE_SECRET_ACCESS_KEY", ""),
        }
        if backend == "s3":
            missing = [f"SW_STORAGE_{name.upper()}" for name, value in values.items() if not value]
            if missing:
                raise ConfigError(f"missing for the s3 backend: {', '.join(missing)}")
        return cls(
            backend=backend,
            root=env.get("SW_STORAGE_ROOT") or "data/",
            image_tag=env.get("SW_IMAGE_TAG") or "local",
            **values,
        )


class Storage(Protocol):
    def read_bytes(self, key: str) -> bytes: ...
    def write_bytes(self, key: str, data: bytes) -> None: ...
    def download(self, key: str, path: Path) -> None: ...
    def upload(self, path: Path, key: str) -> None: ...
    def exists(self, key: str) -> bool: ...
    def list(self, prefix: str) -> list[str]: ...
    def delete(self, key: str) -> None: ...


class LocalStorage:
    """A folder. Writes go to a temporary file first, then `os.replace`."""

    def __init__(self, root: Path) -> None:
        self.root = root

    def _path(self, key: str) -> Path:
        return self.root.joinpath(*key.split("/"))

    def read_bytes(self, key: str) -> bytes:
        try:
            return self._path(key).read_bytes()
        except FileNotFoundError:
            raise ObjectNotFoundError(key) from None

    def write_bytes(self, key: str, data: bytes) -> None:
        target = self._path(key)
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(dir=target.parent, prefix=".tmp-")
        try:
            with os.fdopen(fd, "wb") as handle:
                handle.write(data)
            os.replace(tmp, target)
        except BaseException:
            Path(tmp).unlink(missing_ok=True)
            raise

    def download(self, key: str, path: Path) -> None:
        path.write_bytes(self.read_bytes(key))

    def upload(self, path: Path, key: str) -> None:
        self.write_bytes(key, path.read_bytes())

    def exists(self, key: str) -> bool:
        return self._path(key).is_file()

    def list(self, prefix: str) -> list[str]:
        if not self.root.exists():
            return []
        keys = (
            path.relative_to(self.root).as_posix()
            for path in self.root.rglob("*")
            if path.is_file() and not path.name.startswith(".tmp-")
        )
        return sorted(key for key in keys if key.startswith(prefix))

    def delete(self, key: str) -> None:
        self._path(key).unlink(missing_ok=True)


class S3Storage:
    """An S3-compatible bucket (Cloudflare R2). A put is atomic: readers see all or nothing."""

    def __init__(self, client: S3Client, bucket: str) -> None:
        self.client = client
        self.bucket = bucket

    def read_bytes(self, key: str) -> bytes:
        try:
            body: bytes = self.client.get_object(Bucket=self.bucket, Key=key)["Body"].read()
        except self.client.exceptions.NoSuchKey:
            raise ObjectNotFoundError(key) from None
        return body

    def write_bytes(self, key: str, data: bytes) -> None:
        self.client.put_object(Bucket=self.bucket, Key=key, Body=data)

    def download(self, key: str, path: Path) -> None:
        if not self.exists(key):
            raise ObjectNotFoundError(key)
        self.client.download_file(self.bucket, key, str(path))

    def upload(self, path: Path, key: str) -> None:
        self.client.upload_file(str(path), self.bucket, key)

    def exists(self, key: str) -> bool:
        try:
            self.client.head_object(Bucket=self.bucket, Key=key)
        except self.client.exceptions.ClientError as error:
            if error.response["Error"]["Code"] in ("404", "NoSuchKey", "NotFound"):
                return False
            raise
        return True

    def list(self, prefix: str) -> list[str]:
        keys: list[str] = []
        pages = self.client.get_paginator("list_objects_v2").paginate(
            Bucket=self.bucket, Prefix=prefix
        )
        for page in pages:
            keys.extend(item["Key"] for item in page.get("Contents", []))
        return sorted(keys)

    def delete(self, key: str) -> None:
        self.client.delete_object(Bucket=self.bucket, Key=key)


def from_config(cfg: Config) -> Storage:
    """The only place that chooses the backend."""
    if cfg.backend == "local":
        return LocalStorage(Path(cfg.root))
    import boto3

    kwargs: dict[str, Any] = {
        "endpoint_url": cfg.endpoint,
        "aws_access_key_id": cfg.access_key_id,
        "aws_secret_access_key": cfg.secret_access_key,
        "region_name": "auto",
    }
    return S3Storage(boto3.client("s3", **kwargs), cfg.bucket)
