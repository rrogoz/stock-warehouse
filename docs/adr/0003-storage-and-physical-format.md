# ADR-003: Storage and physical format

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

Runners are ephemeral, so state must live in the bucket ([ADR-002](0002-runtime-and-environments.md)). Bronze must allow full replay (D2), and history must never be overwritten (D13).

## Decision

- **Bronze:** raw payloads exactly as received, one file per source, endpoint and load, in folders by source, endpoint and load date, never by instrument (D10). Append-only, never changed or deleted. A weekly copy of PROD bronze goes to Rafal's disk.
- **Silver and gold:** one DuckDB database file per environment, in its bucket. Each run downloads it, updates it and uploads it under a new dated name; a small pointer file then names the current version, so an interrupted run never leaves a broken current file. The last 14 versions are kept for restore.
- **The database is disposable:** it can always be rebuilt from bronze, and the rebuild is a tested command.
- **D13 in practice:** every silver record carries a business date, a knowledge time and a run id; a correction is a new row; "latest" views pick the newest known version. Names: [ADR-004](0004-physical-data-model.md).
- **Per environment:** DEV builds its own bronze and database in `sw-dev`; the pre-release check builds a throwaway one. PROD data is never copied to DEV.

## Consequences

- One writer at a time per environment.
- Restore is a pointer switch; a full rebuild is always possible.

## Options considered

- Parquet files with DuckDB as the engine.
- A table format on open files (DuckLake, Iceberg, Delta).

**Revisit if** the file grows past a few hundred MB, a second writer appears, or Stage 2 needs open files (first step then: export gold to Parquet).
