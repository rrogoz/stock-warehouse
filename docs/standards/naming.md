# Standard: Naming

One page at most. Skill: `standard-naming`.

## Purpose

Any name tells you its layer and kind, and one concept has one name everywhere ([requirements](../principles.md#what-standards-must-guarantee), [ADR-004](../adr/0004-physical-data-model.md)).

## Rules

- **Case:** lower-case `snake_case` for schemas, tables, columns, config files and Python modules.
- **Schemas** are the layers: `bronze`, `silver`, `gold`.
- **Entity prefix tells the kind:** `fact_` (events and measures), `dim_` (descriptive, SCD2), `ref_` (reference data such as calendars), `map_` (identifier mappings), `ops_` (run log, quarantine). Gold products may add a domain name after the prefix.
- **Column suffix tells the type:** `_id` identifier, `_date` calendar date, `_at` UTC timestamp, `_ccy` ISO 4217 currency code.
- **Business names from silver up.** Source column names appear only in bronze and staging; the source config maps them.
- **Same concept, same name** in every layer and entity: `instrument_code`, `business_date`, `known_at`, `source`. A new name needs a glossary entry.
- **Units and currency are explicit:** in a `_ccy` column or in the entity config's field metadata, never implied.
- **Instruments use the permanent code** patterns of ADR-004 (`FX.EURPLN`, `XWAR.PKN`).
- **Sources and connectors** are named after the source: connector `src/connectors/nbp.py`, config `config/sources/nbp.yaml`.
- **Entity configs** are named after the entity: `config/entities/fact_price_daily.yaml`.
- **Branches** are `<story key>-short-title`; ADR files `NNNN-short-title.md`; specs `docs/specs/SW-NNN.md`.

## Example

NBP's `mid` field arrives in bronze as `mid`. The `nbp` source config maps it to `close` in `silver.fact_price_daily`, with `price_type = fixing` and `quote_ccy = PLN`.

## How it is checked

| Rule | Check | When |
| --- | --- | --- |
| Case, prefixes, suffixes | CI naming check on entity configs and dbt models | M1 |
| Connector and config file names match the source | CI naming check | M1 |
| Branch name carries the story key | CI change check | SW-7 |
| Business names, same concept same name, glossary entry | Review agent | SW-9 |
