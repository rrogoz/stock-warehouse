"""The pipeline run: steps in order, then publish last (SW-16, ADR-007, ADR-003).

The engine owns the run id, the run log and publish. Later stories put their fetch steps in
`STEPS` before `dbt`, which stays last (SW-19).
"""

from __future__ import annotations

import json
import logging
import tempfile
import uuid
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol

import duckdb

from engine import run_log
from engine.dbt_step import DbtStep
from engine.reference import ReferenceStep
from engine.storage import Config, Storage

log = logging.getLogger("engine")

POINTER_KEY = "warehouse/current.json"
DATABASE_PREFIX = "warehouse/sw_"
KEEP = 14


@dataclass(frozen=True)
class RunContext:
    run_id: str
    connection: duckdb.DuckDBPyConnection
    storage: Storage
    database_path: Path
    """The working copy. Steps put scratch files in its folder, which the run deletes."""


class Step(Protocol):
    name: str

    def run(self, ctx: RunContext) -> int:
        """Run the step and return its row count."""
        ...


STEPS: list[Step] = [ReferenceStep(), DbtStep()]


@dataclass(frozen=True)
class RunResult:
    run_id: str
    status: str
    exit_code: int


def _now() -> datetime:
    return datetime.now(UTC)


def _put_json(storage: Storage, key: str, payload: dict[str, object]) -> None:
    storage.write_bytes(key, json.dumps(payload, sort_keys=True).encode())


def _write_ended(
    storage: Storage,
    run_id: str,
    ended_at: datetime,
    status: str,
    counts: dict[str, int],
    failed_step: str | None,
) -> None:
    _put_json(
        storage,
        run_log.ended_key(run_id),
        {
            "run_id": run_id,
            "ended_at": ended_at.isoformat(),
            "status": status,
            "step_row_counts": counts,
            "failed_step": failed_step,
        },
    )


def _fail(
    storage: Storage, run_id: str, counts: dict[str, int], step: str, error: Exception
) -> RunResult:
    log.error("run %s failed in %s: %s", run_id, step, error)
    try:
        _write_ended(storage, run_id, _now(), "failed", counts, step)
    except Exception as write_error:
        log.error("run %s: could not write ended.json: %s", run_id, write_error)
    return RunResult(run_id, "failed", 1)


def run_pipeline(cfg: Config, storage: Storage, steps: Sequence[Step]) -> RunResult:
    run_id = uuid.uuid4().hex
    counts: dict[str, int] = {}
    started_at = _now()
    try:
        _put_json(
            storage,
            run_log.started_key(run_id),
            {"run_id": run_id, "started_at": started_at.isoformat(), "image_tag": cfg.image_tag},
        )
    except Exception as error:
        log.error("run %s failed to start: %s", run_id, error)
        return RunResult(run_id, "failed", 1)

    with tempfile.TemporaryDirectory(prefix="sw-run-") as tmp:
        work = Path(tmp) / "working.duckdb"
        step_name = "prepare"
        try:
            if storage.exists(POINTER_KEY):
                pointer = json.loads(storage.read_bytes(POINTER_KEY))
                storage.download(pointer["database"], work)
            con = duckdb.connect(str(work))
            try:
                run_log.rebuild(con, storage, run_id)
                ctx = RunContext(run_id, con, storage, work)
                for step in steps:
                    step_name = step.name
                    counts[step.name] = step.run(ctx)
                step_name = "publish"
                ended_at = _now()
                run_log.insert_run(
                    con,
                    run_id=run_id,
                    started_at=started_at,
                    ended_at=ended_at,
                    image_tag=cfg.image_tag,
                    step_row_counts=counts,
                )
                # Write the WAL into the file: dbt keeps its own handle on the database open,
                # so closing this connection alone leaves the changes in `working.duckdb.wal`.
                con.execute("checkpoint")
            finally:
                con.close()
            key = f"{DATABASE_PREFIX}{ended_at.strftime('%Y%m%dT%H%M%SZ')}_{run_id}.duckdb"
            storage.upload(work, key)
            _put_json(storage, POINTER_KEY, {"version": 1, "database": key})
        except Exception as error:
            return _fail(storage, run_id, counts, step_name, error)

    _retain(storage, key)
    try:
        _write_ended(storage, run_id, ended_at, "succeeded", counts, None)
    except Exception as error:
        log.error("run %s published but ended.json was not written: %s", run_id, error)
    return RunResult(run_id, "succeeded", 0)


def _retain(storage: Storage, current_key: str) -> None:
    """Delete databases beyond the newest KEEP, never the one the pointer names."""
    try:
        keys = [k for k in storage.list(DATABASE_PREFIX) if k.endswith(".duckdb")]
        for key in sorted(keys, reverse=True)[KEEP:]:
            if key != current_key:
                storage.delete(key)
    except Exception as error:
        log.error("retention failed, the next run retries: %s", error)
