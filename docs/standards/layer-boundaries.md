# Standard: Layer boundaries

One page at most. Skill: `standard-layer-boundaries`.

## Purpose

Each layer reads only from the layer below it, so agents cannot blur the medallion ([requirements](../principles.md#what-standards-must-guarantee), D5, [ADR-006](../adr/0006-transformation-and-data-testing.md)).

## Rules

- **Bronze** is written only by the engine, from connectors. Nothing reads a source except a connector.
- **Staging and silver** read only bronze and reference data (`reference/`, `ref_`, `map_`, `dim_instrument`).
- **Gold** reads only silver. Never bronze, never staging.
- **External producers,** Stage 2 signals included, enter only through bronze as a source, then the contract, then silver.
- **Gold features never depend on signals or portfolios,** so the gold, model, bronze loop is never circular.
- **dbt models reference** other models with `ref()` and bronze with `source()`; no hard-coded schema names.
- **Folders mirror layers:** `dbt/models/staging/`, `dbt/models/silver/`, `dbt/models/gold/`.

## Example

A gold feature that needs a rate reads `ref('fact_price_daily')` from silver. Reading `source('bronze', 'nbp_rates')` from gold fails CI.

## How it is checked

| Rule | Check | When |
| --- | --- | --- |
| Allowed reads per layer | CI layer boundary check on the dbt graph | M1 |
| `ref()` and `source()` only | SQLFluff and the layer boundary check | M1 |
| External producers through bronze; no signal inputs to features | Layer boundary check plus review agent | M1, SW-9 |
