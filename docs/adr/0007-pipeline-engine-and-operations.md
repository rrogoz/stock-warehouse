# ADR-007: Pipeline engine, orchestration and operations

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

Rafal's rule: **configuration over code.** Adding a source or entity should not change the engine, and the same command must run in DEV and PROD.

## Decision

**Engine design**

- **A source is a small connector plus a source config.** The connector has two functions: `fetch` returns the raw response for a request, and `parse` flattens it into a table with the source's own column names. The source config holds the rest: connection settings, instruments, start date, chunk size, rate limit, overlap, and the mapping to the standard format (renames, types, fixed values such as `price_type = fixing`).
- **The engine does everything else, the same way for every source:** works out the requests (history, catch-up, overlap), calls `fetch`, writes the raw file and its metadata to bronze, calls `parse` and saves the flat table next to the raw file, then runs dbt. A parse bug is fixed and re-run from bronze without fetching again.
- **An entity is a config file:** standard columns and types, business key, SCD2 or not, normalisation rules for hashing, allowed values and tests.
- **SQL is generated from config by dbt macros:** staging per source from its column mapping (rename, cast, fixed values, register lookup, quarantine); silver per entity from the entity config (normalise, hash, deduplicate, version, full and incremental). Contracts and tests come from the same config, so they cannot drift. One silver entity serves every source of its data type.
- **Gold is hand-written SQL,** reusing shared macros where they fit.
- **Escape hatch:** an entity config cannot express may have a custom model, with the reason in its spec.
- **Keep config small:** an option is added only when a second entity needs it.

**Running it**

- **One pipeline command:** fetch, check bronze, dbt (silver, tests, completeness gate, gold), publish, run log. GitHub Actions starts it on schedule ([ADR-002](0002-runtime-and-environments.md)).
- **Catch-up by design:** each run loads everything since the last complete session in the run log, plus the 5-session overlap.
- **Run id and run log:** each run's id is stamped on bronze metadata and silver rows; one `ops_run_log` row per run (start, end, status, image tag, row counts per step, gate result).
- **Retries** happen in the fetch step. A failed run is not retried automatically: the next run catches up, or Rafal reruns it.
- **Backfill:** the same command with a date range. In PROD only Rafal starts it; agents backfill in DEV.
- **Deterministic replay:** a past day is recomputed with the code version from its run log row and only the bronze known at that time. A test replays a fixture day.
- **Publish last:** the new database file and pointer switch happen only after every check passes.
- **Logging:** structured console logs (kept 90 days by GitHub); the run log is the permanent record; each run writes a short summary on its GitHub run page.
- **Alerts:** a failed fetch, test or gate fails the job and GitHub emails Rafal. Runs that never started are caught by the daily consistency check ([ADR-010](0010-tracker-and-story-workflow.md)), which also confirms the last weekday's PROD run succeeded (changed 2026-10-28: no Healthchecks.io).

## Consequences

- Adding a source: connector, source config, synthetic samples, register entries. Adding an entity: an entity config. Neither changes the engine.

## Options considered

Dagster or Prefect (a server or cloud account, much more to learn); GitHub Actions steps as the pipeline (cannot run the same way in DEV); our own SQL generator in Python (drops dbt); GitHub failure emails only (misses runs that never start, such as a schedule switched off after 60 days of inactivity).

**Revisit at M4** if the number of sources grows.
