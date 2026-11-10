# ADR-004: Physical data model

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

Principles D3, D4, D6, D7 and D13 need concrete keys, names and load rules that work for every source and asset class.

## Decision

**Identity and keys**

- **Instrument register** in `reference/`: a reviewed file with each instrument's permanent code, current symbol, asset class, exchange, currency and each source's identifiers, all with valid-from and recorded dates. Any new or changed identity is a change Rafal approves (D6 gate).
- **Permanent code:** assigned once, never changed or reused. Patterns: equities `<MIC>.<ticker>` (`XWAR.PKN`), indices `IDX.<name>` (`IDX.WIG20`), FX `FX.<base><quote>` (`FX.EURPLN`), commodities `CMD.<name>` (`CMD.BRENT`), macro `MACRO.<source>.<series>`. On a ticker rename the code stays and the new ticker becomes the current symbol.
- **Silver uses business keys only;** for instruments, the permanent code.
- **Gold may add technical keys** for speed, as a hash of the business key, so they are identical after every full reload. They never leave gold: contracts, external producers and Stage 2 use business keys.
- **Integrity:** every source loads through the register's identifier map. Unknown identifiers are quarantined, never guessed. Tests check that every row points to an existing instrument.

**Structure**

- **Naming:** lower-case snake_case; schemas `bronze`, `silver`, `gold`; prefixes `dim_`, `fact_`, `ref_`, `map_`, `ops_`; suffixes `_id`, `_date`, `_at` (UTC), `_ccy`; units and currency in metadata.
- **Standard silver columns:** `business_date`, `known_at`, `run_id`, `source`, `record_hash`; prices also carry `adjustment_basis` and `price_type` (`ohlc` or `fixing`).
- **M1 entities:** `dim_instrument` and `map_instrument_source` (SCD2, from the register), `fact_price_daily`, `ref_trading_calendar`, `fact_quote_status`, `ops_run_log`, `ops_quarantine`. Corporate events and macro follow at M3.
- **FX:** currency pairs are instruments in `fact_price_daily`.
- **Contracts:** one versioned contract per silver entity (fields, types, business key, version column, rules), used by tests and external producers. Additive by default; a breaking change means a new contract version and a full rebuild, no migration scripts.

**Loading**

- **Full and incremental** loads produce identical, deduplicated silver; a test compares them. Daily runs are incremental; full serves rebuilds, recovery and the pre-release check. Gold is always fully reloaded.
- **Deduplication:** a row is written only when its `record_hash` differs from the latest version for its key. A "current" view holds one row per key.
- **Insert-only versions:** nothing is updated in place; end dates are derived in views. SCD2 key: business key plus valid-from. Price key: instrument, business date and source, versioned by `known_at`.
- **`known_at` comes from bronze:** when the raw file was fetched, never the run time.
- **"As known at" views** show any entity as it was known at a past moment (D11).

**Data rules**

- Each bronze file has a metadata file beside it (source, request, fetch time, run id, row count, checksum).
- Normalise before hashing: fixed decimals, never floats; consistent rounding, nulls and column order; the hash covers value columns only.
- `business_date` is the trading day in the exchange's calendar; all `_at` timestamps are UTC; each FX source states when its day ends.
- Rejected rows go to `ops_quarantine` with a reason; `ops_run_log` records each run.
- Register changes carry a recorded date besides valid-from, so reference data is point in time too.
- Silver stays raw in meaning: no filling of missing days and no currency conversion; only in gold, labelled.

## Consequences

- A rename or a new source never changes a key.
- Every load is replayable and point in time.

## Options considered

Integer IDs from the register; a hash of the current ticker (breaks on a rename); technical keys in silver; IDs generated inside the database; a separate FX table from the start.
