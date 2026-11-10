# Standard: Data modelling

One page at most. Skill: `standard-data-modelling`.

## Purpose

Every entity has a clear grain, key and lineage, and growth adds rows, not tables ([requirements](../principles.md#what-standards-must-guarantee), D3, D4, D7, D8, D13, [ADR-004](../adr/0004-physical-data-model.md)).

## Rules

- **Every entity config declares** its grain in one sentence, its business key and whether it is SCD2.
- **Silver uses business keys only.** Technical keys exist only in gold, as a hash of the business key.
- **One table per entity, never per instrument or asset class.** A new instrument or asset class adds rows (and register entries), never tables or columns.
- **Standard silver columns on every record:** `business_date`, `known_at`, `run_id`, `source`, `record_hash`.
- **Prices also carry** `adjustment_basis` and `price_type`; one series never mixes bases (D7).
- **Silver follows its contract.** Source-specific fields stay in bronze; a field enters silver only when the canonical entity defines it.
- **Insert-only.** Nothing is updated or deleted; a correction is a new version; "current" and "as known at" views derive the rest.
- **Silver is raw in meaning:** no gap filling and no currency conversion. Those happen in gold, labelled.
- **Schema changes are additive by default.** Removing, renaming or retyping a field is a breaking change: new contract version, full rebuild and an ADR.

## Example

`silver.fact_price_daily`: grain "one price per instrument, business date and source, per known version"; key `instrument_code`, `business_date`, `source`, versioned by `known_at`. EUR/PLN, USD/PLN and CHF/PLN are rows in it, not tables.

## How it is checked

| Rule | Check | When |
| --- | --- | --- |
| Grain, key and standard columns declared | Entity config JSON Schema in CI | M1 |
| Contract columns and types | dbt contract on every silver model | M1 |
| Allowed values for `adjustment_basis`, `price_type` | dbt tests | M1 |
| No per-instrument tables or columns | Review agent | SW-9 |
| Breaking change has an ADR and a new contract version | Review agent; code owners on ADRs | SW-9 |
