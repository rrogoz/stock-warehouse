"""No-real-data check: the repository holds code, config, docs and small synthetic fixtures.

Fails when a tracked file is a data store or archive, when a data-shaped file sits
outside the folders allowed to hold one, or when a file is too big to be a fixture.
Whether a fixture is synthetic is left to the review agent (docs/standards/testing.md).
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
# Data stores, data exports and archives: never in the repository (ADR-003).
FORBIDDEN = {
    ".duckdb",
    ".wal",
    ".parquet",
    ".db",
    ".sqlite",
    ".sqlite3",
    ".feather",
    ".arrow",
    ".avro",
    ".orc",
    ".xlsx",
    ".xls",
    ".h5",
    ".hdf5",
    ".pkl",
    ".pickle",
    ".npy",
    ".npz",
    ".zip",
    ".gz",
    ".bz2",
    ".xz",
    ".7z",
    ".tar",
}
# Data-shaped files may live only in these folders.
DATA_SHAPED = {".csv", ".tsv", ".json", ".jsonl", ".ndjson", ".xml"}
DATA_FOLDERS = ("tests/fixtures/", "config/", "reference/", "dbt/", ".claude/")
MAX_BYTES = 500_000
SIZE_EXEMPT = {"uv.lock"}


def tracked_files() -> list[str]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [line for line in out.splitlines() if (ROOT / line).is_file()]


def check(paths: list[str]) -> list[str]:
    errors = []
    for name in paths:
        suffix = Path(name).suffix.lower()
        if suffix in FORBIDDEN:
            errors.append(f"{name}: {suffix} files are data or archives; data lives in storage")
        elif suffix in DATA_SHAPED and not name.startswith(DATA_FOLDERS):
            errors.append(f"{name}: data files belong in {', '.join(DATA_FOLDERS)}")
        size = (ROOT / name).stat().st_size if (ROOT / name).is_file() else 0
        if name not in SIZE_EXEMPT and size > MAX_BYTES:
            errors.append(f"{name}: {size} bytes is over {MAX_BYTES}; fixtures stay small")
    return errors


def main() -> int:
    errors = check(tracked_files())
    for error in errors:
        print(f"no-real-data check: {error}")
    if not errors:
        print("no-real-data check: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
