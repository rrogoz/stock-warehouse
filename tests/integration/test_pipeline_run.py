"""Pipeline runs on LocalStorage with fake steps; no network (SW-16)."""

import json
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import duckdb
import pytest

from engine import pipeline
from engine.__main__ import main
from engine.pipeline import RunContext, run_pipeline
from engine.storage import Config, LocalStorage

POINTER = "warehouse/current.json"


class FakeStep:
    def __init__(self, name: str, rows: int = 0, error: BaseException | None = None) -> None:
        self.name = name
        self.rows = rows
        self.error = error

    def run(self, ctx: RunContext) -> int:
        if self.error:
            raise self.error
        return self.rows


class Kill(BaseException):
    """Not an Exception: the runner does not catch it, like a killed process."""


class FailingWrites(LocalStorage):
    """Fails writes to keys ending with `fail_on`, once `armed`."""

    def __init__(self, root: Path, fail_on: str) -> None:
        super().__init__(root)
        self.fail_on = fail_on

    def write_bytes(self, key: str, data: bytes) -> None:
        if key.endswith(self.fail_on):
            raise OSError("disk full")
        super().write_bytes(key, data)


@pytest.fixture(autouse=True)
def clock(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    now = [datetime(2026, 1, 1, tzinfo=UTC)]

    def tick() -> datetime:
        now[0] += timedelta(seconds=1)
        return now[0]

    monkeypatch.setattr(pipeline, "_now", tick)
    yield


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    return Config.from_env(
        {
            "SW_STORAGE_BACKEND": "local",
            "SW_STORAGE_ROOT": str(tmp_path / "store"),
            "SW_IMAGE_TAG": "test-tag",
        }
    )


@pytest.fixture
def store(cfg: Config) -> LocalStorage:
    return LocalStorage(Path(cfg.root))


def current_rows(store: LocalStorage, tmp_path: Path) -> dict[str, dict[str, Any]]:
    key = json.loads(store.read_bytes(POINTER))["database"]
    copy = tmp_path / "inspect.duckdb"
    store.download(key, copy)
    con = duckdb.connect(str(copy), read_only=True)
    try:
        cur = con.execute(
            "select run_id, status, image_tag, step_row_counts::varchar, failed_step, "
            "business_date::varchar, known_at = started_at, known_at = ended_at, "
            "started_at < ended_at from silver.ops_run_log"
        )
        return {
            r[0]: {
                "status": r[1],
                "image_tag": r[2],
                "counts": json.loads(r[3]) if r[3] else None,
                "failed_step": r[4],
                "date": r[5],
                "known_is_started": r[6],
                "known_is_ended": r[7],
                "ordered": r[8],
            }
            for r in cur.fetchall()
        }
    finally:
        con.close()


def test_run_writes_one_log_row(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    first = run_pipeline(cfg, store, [FakeStep("a", 3), FakeStep("b", 5)])
    first_key = json.loads(store.read_bytes(POINTER))["database"]
    first_rows = current_rows(store, tmp_path)
    second = run_pipeline(cfg, store, [FakeStep("a", 3), FakeStep("b", 5)])
    assert first.run_id != second.run_id
    assert set(first_rows) == {first.run_id}
    rows = current_rows(store, tmp_path)
    assert set(rows) == {first.run_id, second.run_id}
    assert rows[first.run_id] == first_rows[first.run_id]
    for row in rows.values():
        assert row["status"] == "succeeded"
        assert row["image_tag"] == "test-tag"
        assert row["counts"] == {"a": 3, "b": 5}
        assert row["known_is_ended"] and row["ordered"]
        assert row["date"] == "2026-01-01"
    assert first_key != json.loads(store.read_bytes(POINTER))["database"]


def test_ops_run_log_contract(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run_pipeline(cfg, store, [FakeStep("a", 1)])
    with pytest.raises(Kill):
        run_pipeline(cfg, store, [FakeStep("a", error=Kill())])
    run_pipeline(cfg, store, [FakeStep("a", error=ValueError("x"))])
    run_pipeline(cfg, store, [])
    key = json.loads(store.read_bytes(POINTER))["database"]
    copy = tmp_path / "c.duckdb"
    store.download(key, copy)
    con = duckdb.connect(str(copy), read_only=True)
    total, distinct = con.execute(
        "select count(*), count(distinct run_id) from silver.ops_run_log"
    ).fetchone()  # type: ignore[misc]
    assert total == distinct == 4
    nulls = con.execute(
        "select count(*) from silver.ops_run_log where run_id is null or started_at is null "
        "or status is null or image_tag is null or business_date is null or known_at is null"
    ).fetchone()
    assert nulls == (0,)
    statuses = {r[0] for r in con.execute("select status from silver.ops_run_log").fetchall()}
    assert statuses == {"succeeded", "failed", "interrupted"}
    con.close()


def test_publish_switches_pointer(cfg: Config, store: LocalStorage) -> None:
    run_pipeline(cfg, store, [])
    old = json.loads(store.read_bytes(POINTER))["database"]
    old_bytes = store.read_bytes(old)
    result = run_pipeline(cfg, store, [])
    new = json.loads(store.read_bytes(POINTER))["database"]
    assert new != old and new.endswith(f"_{result.run_id}.duckdb")
    assert store.read_bytes(old) == old_bytes


def test_retention_keeps_14(cfg: Config, store: LocalStorage) -> None:
    for _ in range(16):
        run_pipeline(cfg, store, [])
    files = store.list("warehouse/sw_")
    assert len(files) == 14
    assert json.loads(store.read_bytes(POINTER))["database"] in files


def test_failing_download_is_prepare(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run_pipeline(cfg, store, [])
    store.delete(json.loads(store.read_bytes(POINTER))["database"])
    result = run_pipeline(cfg, store, [FakeStep("a", 1)])
    assert (result.status, result.exit_code) == ("failed", 1)
    ended = json.loads(store.read_bytes(f"ops/run_log/{result.run_id}/ended.json"))
    assert ended["status"] == "failed" and ended["failed_step"] == "prepare"


def test_failing_step(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run_pipeline(cfg, store, [FakeStep("a", 1)])
    pointer, key = store.read_bytes(POINTER), json.loads(store.read_bytes(POINTER))["database"]
    data = store.read_bytes(key)
    result = run_pipeline(cfg, store, [FakeStep("ok", 2), FakeStep("bad", error=ValueError("x"))])
    assert (result.status, result.exit_code) == ("failed", 1)
    assert store.read_bytes(POINTER) == pointer and store.read_bytes(key) == data
    ended = json.loads(store.read_bytes(f"ops/run_log/{result.run_id}/ended.json"))
    assert ended["status"] == "failed" and ended["failed_step"] == "bad"
    run_pipeline(cfg, store, [])
    row = current_rows(store, tmp_path)[result.run_id]
    assert row["status"] == "failed" and row["failed_step"] == "bad"
    assert row["counts"] == {"ok": 2}


def test_interrupted_run(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run_pipeline(cfg, store, [])
    pointer = store.read_bytes(POINTER)
    before = set(store.list("ops/run_log/"))
    with pytest.raises(Kill):
        run_pipeline(cfg, store, [FakeStep("a", error=Kill())])
    assert store.read_bytes(POINTER) == pointer
    (started,) = set(store.list("ops/run_log/")) - before
    assert started.endswith("started.json")
    run_pipeline(cfg, store, [])
    killed = started.split("/")[2]
    row = current_rows(store, tmp_path)[killed]
    assert row["status"] == "interrupted" and row["known_is_started"]
    run_pipeline(cfg, store, [])
    assert current_rows(store, tmp_path)[killed]["status"] == "interrupted"


def test_interrupted_publish(cfg: Config, tmp_path: Path) -> None:
    store = LocalStorage(Path(cfg.root))
    run_pipeline(cfg, store, [])
    pointer = store.read_bytes(POINTER)
    broken = FailingWrites(Path(cfg.root), "current.json")
    result = run_pipeline(cfg, broken, [FakeStep("a", 1)])
    assert result.exit_code == 1
    assert store.read_bytes(POINTER) == pointer
    ended = json.loads(store.read_bytes(f"ops/run_log/{result.run_id}/ended.json"))
    assert ended["failed_step"] == "publish"


def test_ended_write_fails_after_publish(cfg: Config, tmp_path: Path) -> None:
    store = LocalStorage(Path(cfg.root))
    broken = FailingWrites(Path(cfg.root), "ended.json")
    result = run_pipeline(cfg, broken, [FakeStep("a", 1)])
    assert result.exit_code == 0
    assert json.loads(store.read_bytes(POINTER))["database"].endswith(f"{result.run_id}.duckdb")
    run_pipeline(cfg, store, [])
    row = current_rows(store, tmp_path)[result.run_id]
    assert row["status"] == "succeeded" and row["counts"] == {"a": 1}


def test_run_summary_line(
    monkeypatch: pytest.MonkeyPatch, cfg: Config, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("SW_STORAGE_BACKEND", "local")
    monkeypatch.setenv("SW_STORAGE_ROOT", cfg.root)
    assert main(["run"]) == 0
    last = capsys.readouterr().out.strip().splitlines()[-1]
    run_id = (
        json.loads(LocalStorage(Path(cfg.root)).read_bytes(POINTER))["database"]
        .rsplit("_", 1)[1]
        .removesuffix(".duckdb")
    )
    assert last == f"run {run_id} succeeded"


def test_run_bad_configuration_exits_2(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("SW_STORAGE_BACKEND", raising=False)
    assert main(["run"]) == 2
