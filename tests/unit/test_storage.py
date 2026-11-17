"""Storage contract tests, run on LocalStorage and on S3Storage against moto (SW-16)."""

from collections.abc import Iterator
from pathlib import Path

import boto3
import pytest
from moto import mock_aws

from engine.storage import (
    Config,
    ConfigError,
    LocalStorage,
    ObjectNotFoundError,
    S3Storage,
    Storage,
    from_config,
)


@pytest.fixture(params=["local", "s3"])
def storage(request: pytest.FixtureRequest, tmp_path: Path) -> Iterator[Storage]:
    if request.param == "local":
        yield LocalStorage(tmp_path / "root")
        return
    with mock_aws():
        client = boto3.client("s3", region_name="us-east-1")
        client.create_bucket(Bucket="sw-test")
        yield S3Storage(client, "sw-test")


def test_write_read_exists_delete(storage: Storage) -> None:
    assert not storage.exists("a/b.json")
    storage.write_bytes("a/b.json", b"one")
    storage.write_bytes("a/b.json", b"two")
    assert storage.exists("a/b.json")
    assert storage.read_bytes("a/b.json") == b"two"
    storage.delete("a/b.json")
    storage.delete("a/b.json")
    assert not storage.exists("a/b.json")


def test_missing_key_raises(storage: Storage, tmp_path: Path) -> None:
    with pytest.raises(ObjectNotFoundError):
        storage.read_bytes("nope")
    with pytest.raises(ObjectNotFoundError):
        storage.download("nope", tmp_path / "x")


def test_list_by_prefix_sorted(storage: Storage) -> None:
    for key in ("w/b", "w/a", "x/c", "w/sub/d"):
        storage.write_bytes(key, b"")
    assert storage.list("w/") == ["w/a", "w/b", "w/sub/d"]
    assert storage.list("none/") == []


def test_upload_download_round_trip(storage: Storage, tmp_path: Path) -> None:
    source = tmp_path / "src.bin"
    source.write_bytes(b"payload")
    storage.upload(source, "k/file.bin")
    target = tmp_path / "dst.bin"
    storage.download("k/file.bin", target)
    assert target.read_bytes() == b"payload"


def test_local_write_leaves_no_temporary_file(tmp_path: Path) -> None:
    store = LocalStorage(tmp_path)
    store.write_bytes("a/b", b"x")
    assert [p.name for p in (tmp_path / "a").iterdir()] == ["b"]


def test_from_config_picks_by_backend(tmp_path: Path) -> None:
    local = Config.from_env({"SW_STORAGE_BACKEND": "local", "SW_STORAGE_ROOT": str(tmp_path)})
    assert isinstance(from_config(local), LocalStorage)
    s3 = Config.from_env(
        {
            "SW_STORAGE_BACKEND": "s3",
            "SW_STORAGE_ENDPOINT": "https://example.invalid",
            "SW_STORAGE_BUCKET": "b",
            "SW_STORAGE_ACCESS_KEY_ID": "id",
            "SW_STORAGE_SECRET_ACCESS_KEY": "secret",
        }
    )
    assert isinstance(from_config(s3), S3Storage)


def test_config_defaults() -> None:
    cfg = Config.from_env({"SW_STORAGE_BACKEND": "local"})
    assert cfg.root == "data/"
    assert cfg.image_tag == "local"


@pytest.mark.parametrize(
    "env",
    [
        {},
        {"SW_STORAGE_BACKEND": "gcs"},
        {"SW_STORAGE_BACKEND": "s3"},
        {"SW_STORAGE_BACKEND": "s3", "SW_STORAGE_ENDPOINT": "https://e", "SW_STORAGE_BUCKET": "b"},
    ],
)
def test_config_errors(env: dict[str, str]) -> None:
    with pytest.raises(ConfigError):
        Config.from_env(env)
