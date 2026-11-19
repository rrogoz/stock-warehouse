"""Step `reference`: flatten the instrument register into the run folder (docs/specs/SW-19.md).

Writes `<run folder>/reference/instrument_versions.jsonl` and `instrument_source_ids.jsonl`,
one JSON object per line with every key present, nulls included, for the dbt staging models.
Flattening only, no logic: the register is checked by its schema in the tests (SW-14).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING, Any

import yaml

if TYPE_CHECKING:
    from engine.pipeline import RunContext


REGISTER = Path(__file__).resolve().parents[2] / "reference" / "instrument_register.yaml"
VERSION_FIELDS = (
    "valid_from_date",
    "recorded_date",
    "current_symbol",
    "asset_class",
    "exchange",
    "quote_ccy",
)
SOURCE_ID_FIELDS = ("source", "source_instrument_id", "valid_from_date", "recorded_date")


def reference_dir(ctx: RunContext) -> Path:
    """Folder of the reference files in the run folder; the run deletes it."""
    return ctx.database_path.parent / "reference"


def flatten(register: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """File name to rows, in register order."""
    versions, source_ids = [], []
    for code, instrument in register["instruments"].items():
        for entry in instrument["versions"]:
            versions.append({"instrument_code": code} | {k: entry.get(k) for k in VERSION_FIELDS})
        for entry in instrument["source_ids"]:
            source_ids.append(
                {"instrument_code": code} | {k: entry.get(k) for k in SOURCE_ID_FIELDS}
            )
    return {"instrument_versions": versions, "instrument_source_ids": source_ids}


class ReferenceStep:
    name = "reference"

    def __init__(self, register: Path = REGISTER) -> None:
        self.register = register

    def run(self, ctx: RunContext) -> int:
        register = yaml.safe_load(self.register.read_text(encoding="utf-8"))
        out = reference_dir(ctx)
        out.mkdir(parents=True, exist_ok=True)
        rows = 0
        for name, records in flatten(register).items():
            lines = "".join(json.dumps(r, sort_keys=False) + "\n" for r in records)
            (out / f"{name}.jsonl").write_text(lines, encoding="utf-8")
            rows += len(records)
        return rows
