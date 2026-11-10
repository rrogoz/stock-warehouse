# Standard: Testing

One page at most. Skill: `standard-testing`.

## Purpose

Every entity, layer and connector is tested on synthetic data, and a failing test stops promotion ([requirements](../principles.md#what-standards-must-guarantee), D9, D11, D14, [ADR-006](../adr/0006-transformation-and-data-testing.md)).

## Rules

- **Every entity:** unique business key plus version, required fields not null, every instrument exists in the register, its own business rules.
- **Bronze:** expected files and rows arrived, checked against the metadata files.
- **Silver:** the contract holds; every expected instrument and session is present or has a quote status (completeness gate, D14); price sanity (high at least low, prices above zero).
- **Gold:** value ranges and no look-ahead (D11).
- **Every connector** has a contract test on synthetic sample responses shaped like the real ones. Tests never call a real source.
- **Full equals incremental:** both modes on the same fixture bronze give identical silver.
- **Fixtures are synthetic** and live in `tests/fixtures/`. They cover holiday, missing day, late correction, duplicate re-fetch and ticker rename. No real market data.
- **Folders:** `tests/unit/` (Python logic), `tests/contract/` (connectors), `tests/integration/` (pipeline and dbt on fixtures); data tests live with dbt.
- **Every bug fix adds a test** that fails without the fix.
- **A failing test blocks merge and promotion;** the completeness gate also blocks the gold rebuild.

## Example

`tests/contract/test_nbp.py` parses a synthetic NBP response for `FX.EURPLN` covering a Polish holiday, and asserts the flat table has the columns the `nbp` source config maps.

## How it is checked

| Rule | Check | When |
| --- | --- | --- |
| pytest suite passes | CI tests | SW-7 |
| No real data in fixtures | CI no-real-data check | SW-7 |
| Entity, layer and gate tests; full equals incremental | dbt build on fixtures in CI | M1 |
| Every entity and connector has its tests | CI coverage check plus review agent | M1, SW-9 |
| Bug fix adds a test | Review agent | SW-9 |
