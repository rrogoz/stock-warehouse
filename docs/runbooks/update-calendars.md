# Runbook: Update the trading calendars

Numbered steps only. Files, format and generator: [SW-17](../specs/SW-17.md), the [schema](../../config/schemas/trading_calendar.schema.json) and `src/engine/calendars.py`; the decision: [ADR-005](../adr/0005-sources-and-ingestion.md).

## When to use

Each autumn, to add the next year; or after a `exchange-calendars` or `holidays` upgrade.

## Steps

1. Raise `LAST_YEAR` in `src/engine/calendars.py` to the next year and the expected file count in `test_files_cover_all_years`. The generator refuses a year past `LAST_YEAR`.
2. Next year: `uv sync`, then `uv run python -m engine.calendars --from-year <next> --to-year <next>`. Unchanged files keep their `recorded_date`.
3. Check each new file's closures against the GPW trading calendar and the government's list of days off; a missing ad hoc closure is added by upgrading the library, never by editing a file by hand.
4. Open a pull request for Rafal, one story, with the new files.
5. After a library upgrade: `uv run python -m engine.calendars --check`. If it exits 1, run the generator without `--check` and review the diff of every changed past year.

## How to check it worked

- `uv run pytest tests/unit/test_calendars.py` passes and `--check` exits 0.
- The pull request shows only closure lines and new `recorded_date` values for changed years.
