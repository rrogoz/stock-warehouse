"""The run log: `silver.ops_run_log`, rebuilt from `ops/run_log/` objects (SW-16, ADR-007).

The objects are the permanent record, insert-only and written outside the database file. Each
run rebuilds the table from them, so a row is a function of its run's objects and never
changes. `ended.json` wins; without it the run keeps the row its published copy already holds
(a run whose `ended.json` write failed after publish); only a run with neither is `interrupted`.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import duckdb
import yaml

from engine.storage import Storage

ENTITY_FILE = Path(__file__).resolve().parents[2] / "config" / "entities" / "ops_run_log.yaml"
PREFIX = "ops/run_log/"
TABLE = "silver.ops_run_log"
SQL_TYPES = {"varchar": "varchar", "date": "date", "timestamptz": "timestamptz", "json": "json"}


def started_key(run_id: str) -> str:
    return f"{PREFIX}{run_id}/started.json"


def ended_key(run_id: str) -> str:
    return f"{PREFIX}{run_id}/ended.json"


def load_entity(path: Path = ENTITY_FILE) -> dict[str, Any]:
    entity: dict[str, Any] = yaml.safe_load(path.read_text(encoding="utf-8"))
    return entity


def columns(entity: dict[str, Any]) -> list[str]:
    return [field["name"] for field in entity["fields"]]


def create_table_sql(entity: dict[str, Any], table: str = TABLE) -> str:
    parts = []
    for field in entity["fields"]:
        part = f"{field['name']} {SQL_TYPES[field['type']]}"
        if field["required"]:
            part += " not null"
        if "allowed" in field:
            allowed = ", ".join(f"'{value}'" for value in field["allowed"])
            part += f" check ({field['name']} in ({allowed}))"
        parts.append(part)
    parts.append(f"primary key ({', '.join(entity['business_key'])})")
    return f"create table {table} ({', '.join(parts)})"


def _insert(con: duckdb.DuckDBPyConnection, row: dict[str, Any]) -> None:
    names = list(row)
    marks = ", ".join(
        "?::json"
        if name == "step_row_counts"
        else "?::timestamptz"
        if name.endswith("_at")
        else "?"
        for name in names
    )
    con.execute(
        f"insert into {TABLE} ({', '.join(names)}) values ({marks})",
        [json.dumps(v) if n == "step_row_counts" and v is not None else v for n, v in row.items()],
    )


def insert_run(
    con: duckdb.DuckDBPyConnection,
    *,
    run_id: str,
    started_at: datetime,
    ended_at: datetime,
    image_tag: str,
    step_row_counts: dict[str, int],
) -> None:
    """The row of a run that is about to be published (step 5)."""
    _insert(
        con,
        {
            "run_id": run_id,
            "business_date": started_at.astimezone(UTC).date().isoformat(),
            "known_at": ended_at.isoformat(),
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
            "status": "succeeded",
            "image_tag": image_tag,
            "step_row_counts": step_row_counts,
            "failed_step": None,
        },
    )


def _run_ids(storage: Storage) -> list[str]:
    ids = {key[len(PREFIX) :].split("/", 1)[0] for key in storage.list(PREFIX)}
    return sorted(ids)


def rebuild(con: duckdb.DuckDBPyConnection, storage: Storage, current_run_id: str) -> None:
    """Rebuild `silver.ops_run_log` from the run log objects; the current run is left out."""
    entity = load_entity()
    cols = ", ".join(columns(entity))
    con.execute("create schema if not exists silver")
    has_old = bool(
        con.execute(
            "select 1 from information_schema.tables "
            "where table_schema = 'silver' and table_name = 'ops_run_log'"
        ).fetchone()
    )
    if has_old:
        con.execute(f"alter table {TABLE} rename to ops_run_log_prev")
    con.execute(create_table_sql(entity))
    for run_id in _run_ids(storage):
        if run_id == current_run_id or not storage.exists(started_key(run_id)):
            continue
        if storage.exists(ended_key(run_id)):
            started = json.loads(storage.read_bytes(started_key(run_id)))
            ended = json.loads(storage.read_bytes(ended_key(run_id)))
            _insert(
                con,
                {
                    "run_id": run_id,
                    "business_date": _date(started["started_at"]),
                    "known_at": ended["ended_at"],
                    "started_at": started["started_at"],
                    "ended_at": ended["ended_at"],
                    "status": ended["status"],
                    "image_tag": started["image_tag"],
                    "step_row_counts": ended.get("step_row_counts"),
                    "failed_step": ended.get("failed_step"),
                },
            )
            continue
        if has_old:
            kept = con.execute(
                f"insert into {TABLE} ({cols}) select {cols} "
                "from silver.ops_run_log_prev where run_id = ? returning run_id",
                [run_id],
            ).fetchall()
            if kept:
                continue
        started = json.loads(storage.read_bytes(started_key(run_id)))
        _insert(
            con,
            {
                "run_id": run_id,
                "business_date": _date(started["started_at"]),
                "known_at": started["started_at"],
                "started_at": started["started_at"],
                "ended_at": None,
                "status": "interrupted",
                "image_tag": started["image_tag"],
                "step_row_counts": None,
                "failed_step": None,
            },
        )
    if has_old:
        con.execute("drop table silver.ops_run_log_prev")


def _date(stamp: str) -> str:
    return datetime.fromisoformat(stamp).astimezone(UTC).date().isoformat()
