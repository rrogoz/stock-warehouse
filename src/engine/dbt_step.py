"""Step `dbt`: `dbt build` on the working copy, in process (docs/specs/SW-19.md, ADR-006).

The profile, `target/` and `logs/` go to the run folder: the image's `/app` is read-only. A
failed model or test raises, so the run fails and nothing is published (SW-16).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import duckdb
import yaml
from dbt.cli.main import dbtRunner, dbtRunnerResult

from engine import dbt_models
from engine.reference import reference_dir

if TYPE_CHECKING:
    from engine.pipeline import RunContext

PROJECT_DIR = Path(__file__).resolve().parents[2] / "dbt"
PROFILE = "stock_warehouse"


class DbtError(Exception):
    """dbt failed: a model, a test or the project."""


def invoke(
    command: str, database_path: Path, *, run_id: str, reference: Path, full_refresh: bool = False
) -> dbtRunnerResult:
    """Run one dbt command on `database_path`; scratch files go next to it."""
    folder = database_path.parent / "dbt"
    folder.mkdir(parents=True, exist_ok=True)
    profile = {
        PROFILE: {
            "target": "run",
            "outputs": {"run": {"type": "duckdb", "path": str(database_path), "threads": 1}},
        }
    }
    (folder / "profiles.yml").write_text(yaml.safe_dump(profile), encoding="utf-8")
    args = [
        command,
        "--project-dir",
        str(PROJECT_DIR),
        "--profiles-dir",
        str(folder),
        "--target-path",
        str(folder / "target"),
        "--log-path",
        str(folder / "logs"),
        "--vars",
        json.dumps({"run_id": run_id, "reference_dir": str(reference)}),
    ]
    if full_refresh:
        args.append("--full-refresh")
    return dbtRunner().invoke(args)


def _rows(con: duckdb.DuckDBPyConnection, tables: list[str]) -> int:
    total = 0
    for table in tables:
        exists = con.execute(
            "select 1 from information_schema.tables "
            "where table_schema = 'silver' and table_name = ?",
            [table],
        ).fetchone()
        if exists:
            count = con.execute(f"select count(*) from silver.{table}").fetchone()
            total += count[0] if count else 0
    return total


class DbtStep:
    name = "dbt"

    def __init__(self, full_refresh: bool = False) -> None:
        self.full_refresh = full_refresh

    def run(self, ctx: RunContext) -> int:
        """Build every model and run every test; return the rows inserted into silver."""
        tables = [e["entity"] for e in dbt_models.load_entities() if e["built_by"] == "dbt"]
        before = 0 if self.full_refresh else _rows(ctx.connection, tables)
        result = invoke(
            "build",
            ctx.database_path,
            run_id=ctx.run_id,
            reference=reference_dir(ctx),
            full_refresh=self.full_refresh,
        )
        if not result.success:
            raise DbtError(f"dbt build failed: {result.exception or 'a model or test failed'}")
        return _rows(ctx.connection, tables) - before
