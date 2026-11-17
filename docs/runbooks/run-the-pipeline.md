# Runbook: Run the pipeline

Numbered steps only.

## When to use

You run `python -m engine run` in DEV, for example Rafal's first run on Windows with Docker Desktop, or you need to read the run log or restore an older warehouse version.

## Steps

Part 1: first run on Windows with Docker Desktop (DEV only).

1. In PowerShell, in the repository folder: `Copy-Item .env.example .env`.
2. In `.env` set `SW_STORAGE_BACKEND=s3`, `SW_STORAGE_ENDPOINT` to the DEV R2 endpoint, `SW_STORAGE_BUCKET=sw-dev`, and the DEV R2 key in `SW_STORAGE_ACCESS_KEY_ID` and `SW_STORAGE_SECRET_ACCESS_KEY`. Never put PROD values here.
3. Build: `docker build --build-arg SW_IMAGE_TAG=dev-first -t sw:dev-first .`
4. Run: `docker run --rm --env-file .env sw:dev-first run`
5. Check `$LASTEXITCODE`: 0 is success, 1 a failed step or publish, 2 bad configuration (the message names the missing setting).
6. Check the last output line is `run <run_id> succeeded`.
7. In bucket `sw-dev` check the new `warehouse/sw_<date>_<run_id>.duckdb`, that `warehouse/current.json` names it, and that `ops/run_log/<run_id>/ended.json` says `succeeded`.
8. To read the run log row, download the file `current.json` names and run `SELECT * FROM silver.ops_run_log` in the DuckDB CLI.

Part 2: read the run log and restore.

1. Read the log: `ops/run_log/<run_id>/started.json` and `ended.json` per run; a run with no `ended.json` was interrupted or its end was not recorded. `silver.ops_run_log` in the current file lists them all.
2. Restore an older version: pick a file `warehouse/sw_<date>_<run_id>.duckdb` from the bucket (the newest 14 are kept) and overwrite `warehouse/current.json` with `{"version": 1, "database": "warehouse/sw_<date>_<run_id>.duckdb"}`. Data files are never edited.

## How to check it worked

The run ends with `run <run_id> succeeded` and exit code 0, `warehouse/current.json` names a new database file, and `ops/run_log/<run_id>/ended.json` says `succeeded`. After a restore, the next run starts from the file the pointer names.
