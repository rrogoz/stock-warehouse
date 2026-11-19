"""dim_instrument and map_instrument_source built by dbt on synthetic registers (SW-19).

Each test runs the pipeline on LocalStorage in `tmp_path`, with the fixture register in
`tests/fixtures/reference/`; no network.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb
import pytest

from engine import dbt_step, pipeline
from engine.dbt_step import DbtStep
from engine.pipeline import RunResult, run_pipeline
from engine.reference import ReferenceStep
from engine.storage import Config, LocalStorage

FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "reference"
STATE_1 = FIXTURES / "state_1" / "instrument_register.yaml"
STATE_2 = FIXTURES / "state_2" / "instrument_register.yaml"
POINTER = "warehouse/current.json"
TABLES = {
    "dim_instrument": "instrument_code, valid_from_date, known_at",
    "map_instrument_source": "instrument_code, source, valid_from_date, known_at",
}


@pytest.fixture
def cfg(tmp_path: Path) -> Config:
    return Config.from_env({"SW_STORAGE_BACKEND": "local", "SW_STORAGE_ROOT": str(tmp_path / "s")})


@pytest.fixture
def store(cfg: Config) -> LocalStorage:
    return LocalStorage(Path(cfg.root))


def run(cfg: Config, store: LocalStorage, register: Path, full: bool = False) -> RunResult:
    return run_pipeline(cfg, store, [ReferenceStep(register), DbtStep(full_refresh=full)])


def published(store: LocalStorage, tmp_path: Path) -> Path:
    key = json.loads(store.read_bytes(POINTER))["database"]
    copy = tmp_path / f"copy_{key.rsplit('_', 1)[1]}"
    store.download(key, copy)
    return copy


def rows(store: LocalStorage, tmp_path: Path, table: str, cols: str = "*") -> list[tuple[Any, ...]]:
    con = duckdb.connect(str(published(store, tmp_path)), read_only=True)
    try:
        sql = f"select {cols} from silver.{table} order by {TABLES[table]}"
        return con.execute(sql).fetchall()
    finally:
        con.close()


def md5(*values: str | None) -> str:
    text = "\x1f".join("\\N" if v is None else v for v in values)
    return hashlib.md5(text.encode()).hexdigest()


def write(tmp_path: Path, text: str) -> Path:
    path = tmp_path / "register" / "instrument_register.yaml"
    path.parent.mkdir(exist_ok=True)
    path.write_text(text)
    return path


def test_dbt_is_last_step() -> None:
    assert [step.name for step in pipeline.STEPS] == ["reference", "dbt"]


def test_pipeline_builds_reference_entities(
    cfg: Config, store: LocalStorage, tmp_path: Path
) -> None:
    result = run(cfg, store, STATE_1)
    assert result.exit_code == 0
    con = duckdb.connect(str(published(store, tmp_path)), read_only=True)
    tables = con.execute(
        "select table_name from information_schema.tables where table_schema = 'silver'"
    ).fetchall()
    (counts,) = con.execute(
        "select step_row_counts::varchar from silver.ops_run_log where run_id = ?",
        [result.run_id],
    ).fetchone()  # type: ignore[misc]
    con.close()
    assert {t[0] for t in tables} == {"dim_instrument", "map_instrument_source", "ops_run_log"}
    assert json.loads(counts) == {"reference": 4, "dbt": 4}


def test_reference_entities_from_state_1(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run_id = run(cfg, store, STATE_1).run_id
    known = "2026-01-05 00:00:00+00"
    dim = rows(
        store,
        tmp_path,
        "dim_instrument",
        "instrument_code, valid_from_date::varchar, current_symbol, asset_class, exchange, "
        "quote_ccy, strftime(known_at at time zone 'UTC', '%Y-%m-%d %H:%M:%S+00'), run_id, "
        "record_hash",
    )
    assert dim == [
        ("FX.AAAPLN", "2020-01-02", "AAAPLN", "fx", None, "PLN", known, run_id,
         md5("AAAPLN", "fx", None, "PLN")),
        ("FX.BBBPLN", "2020-01-02", "BBBPLN", "fx", None, "PLN", known, run_id,
         md5("BBBPLN", "fx", None, "PLN")),
    ]  # fmt: skip
    mapping = rows(
        store,
        tmp_path,
        "map_instrument_source",
        "instrument_code, source, valid_from_date::varchar, source_instrument_id, "
        "strftime(known_at at time zone 'UTC', '%Y-%m-%d %H:%M:%S+00'), run_id, record_hash",
    )
    assert mapping == [
        ("FX.AAAPLN", "nbp", "2020-01-02", "A/AAA", known, run_id, md5("A/AAA")),
        ("FX.BBBPLN", "nbp", "2020-01-02", "A/BBB", known, run_id, md5("A/BBB")),
    ]


def test_insert_only(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run(cfg, store, STATE_1)
    before = {t: rows(store, tmp_path, t) for t in TABLES}
    second = run(cfg, store, STATE_2)
    after = {t: rows(store, tmp_path, t) for t in TABLES}
    for table in TABLES:
        assert set(before[table]) <= set(after[table])
    dim_new = sorted(set(after["dim_instrument"]) - set(before["dim_instrument"]))
    map_new = sorted(set(after["map_instrument_source"]) - set(before["map_instrument_source"]))
    assert [(r[0], r[2]) for r in dim_new] == [("FX.BBBPLN", "BBXPLN"), ("FX.CCCPLN", "CCCPLN")]
    assert [(r[0], r[3]) for r in map_new] == [("FX.AAAPLN", "B/AAA"), ("FX.CCCPLN", "A/CCC")]
    assert {r[7] for r in dim_new} | {r[5] for r in map_new} == {second.run_id}
    renamed = [r[2] for r in after["dim_instrument"] if r[0] == "FX.BBBPLN"]
    assert renamed == ["BBBPLN", "BBXPLN"]

    rerun = run(cfg, store, STATE_2)
    assert rerun.exit_code == 0
    assert {t: rows(store, tmp_path, t) for t in TABLES} == after
    con = duckdb.connect(str(published(store, tmp_path)), read_only=True)
    (counts,) = con.execute(
        "select step_row_counts::varchar from silver.ops_run_log where run_id = ?",
        [rerun.run_id],
    ).fetchone()  # type: ignore[misc]
    con.close()
    assert json.loads(counts)["dbt"] == 0


def without_run_id(store: LocalStorage, tmp_path: Path) -> dict[str, list[tuple[Any, ...]]]:
    out = {}
    for table in TABLES:
        con = duckdb.connect(str(published(store, tmp_path)), read_only=True)
        out[table] = con.execute(
            f"select * exclude (run_id) from silver.{table} order by {TABLES[table]}"
        ).fetchall()
        con.close()
    return out


def test_full_equals_incremental(cfg: Config, tmp_path: Path) -> None:
    incremental = LocalStorage(tmp_path / "incremental")
    run(cfg, incremental, STATE_1)
    run(cfg, incremental, STATE_2)
    full = LocalStorage(tmp_path / "full")
    run(cfg, full, STATE_2, full=True)
    expected = without_run_id(full, tmp_path)
    assert without_run_id(incremental, tmp_path) == expected
    assert [r[2] for r in expected["dim_instrument"] if r[0] == "FX.BBBPLN"] == [
        "BBBPLN",
        "BBXPLN",
    ]


def test_full_build_replaces_tables(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run(cfg, store, STATE_2)
    first = without_run_id(store, tmp_path)
    result = run(cfg, store, STATE_2, full=True)
    assert result.exit_code == 0
    assert without_run_id(store, tmp_path) == first


def test_duplicate_key_fails_run(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run(cfg, store, STATE_1)
    pointer = store.read_bytes(POINTER)
    text = STATE_2.read_text().replace(
        "        current_symbol: CCCPLN\n        asset_class: fx\n        quote_ccy: PLN\n",
        "        current_symbol: CCCPLN\n        asset_class: fx\n        quote_ccy: PLN\n"
        '      - valid_from_date: "2026-02-02"\n        recorded_date: "2026-02-03"\n'
        "        current_symbol: CCXPLN\n        asset_class: fx\n        quote_ccy: PLN\n",
    )
    assert text != STATE_2.read_text()
    result = run(cfg, store, write(tmp_path, text))
    assert (result.status, result.exit_code) == ("failed", 1)
    assert store.read_bytes(POINTER) == pointer
    ended = json.loads(store.read_bytes(f"ops/run_log/{result.run_id}/ended.json"))
    assert ended["failed_step"] == "dbt"


def test_relationship_test_fails(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run(cfg, store, STATE_1)
    work = tmp_path / "broken" / "working.duckdb"
    work.parent.mkdir()
    work.write_bytes(published(store, tmp_path).read_bytes())
    con = duckdb.connect(str(work))
    con.execute("delete from silver.dim_instrument where instrument_code = 'FX.AAAPLN'")
    con.close()
    result = dbt_step.invoke("test", work, run_id="test", reference=tmp_path / "unused")
    assert not result.success
    failed = {r.node.name for r in result.result if r.status == "fail"}  # type: ignore[union-attr]
    assert failed == {
        "relationships_map_instrument_source_instrument_code__instrument_code__ref_dim_instrument_"
    }


def test_same_day_correction_fails(cfg: Config, store: LocalStorage, tmp_path: Path) -> None:
    run(cfg, store, STATE_1)
    pointer = store.read_bytes(POINTER)
    corrected = write(tmp_path, STATE_1.read_text().replace("A/AAA", "A/AAX"))
    result = run(cfg, store, corrected)
    assert (result.status, result.exit_code) == ("failed", 1)
    assert store.read_bytes(POINTER) == pointer

    full = run(cfg, store, corrected, full=True)
    assert full.exit_code == 0
    ids = [r[3] for r in rows(store, tmp_path, "map_instrument_source")]
    assert ids == ["A/AAX", "A/BBB"]
