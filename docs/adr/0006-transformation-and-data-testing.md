# ADR-006: Transformation and data testing

- **Status:** Accepted
- **Date:** 2026-10-26

## Context

Silver and gold need ordered SQL transformations, data tests, documentation and lineage, at zero cost.

## Decision

- **dbt Core with the DuckDB adapter.** All SQL transformations, tests and model docs live in one dbt project in `dbt/`.
- **Layer mapping:** staging per source and silver per entity are generated from config by dbt macros ([ADR-007](0007-pipeline-engine-and-operations.md)). Silver is insert-only and deduplicated: incremental mode adds only rows with a new `record_hash`; a full run rebuilds from all of bronze ([ADR-004](0004-physical-data-model.md)). Gold is rebuilt in full every run.
- **Tests on every entity:** contract enforced (columns and types); unique key plus version; required fields; every instrument exists in the register; allowed values (`price_type`, `adjustment_basis`).
- **Per layer:** bronze, expected files and rows arrived (from metadata files); silver, every expected instrument and session is present or has a quote status (the completeness gate, D14), plus price sanity (high at least low, prices above zero); gold, value ranges and no look-ahead.
- **Full equals incremental:** a test runs both modes on the same fixture bronze and compares.
- **The completeness gate blocks gold:** if it fails, gold is not rebuilt and the run fails visibly.
- **Fixtures:** synthetic bronze files covering holiday, missing day, late correction, duplicate re-fetch, ticker rename. The pre-release check on real data catches drift between fixtures and reality.
- **Layer boundaries enforced by CI:** a check fails if silver reads gold, or gold reads bronze.
- **Adjusted series (D7):** at M1 gold passes prices through with their adjustment basis; derived adjustments arrive with corporate events at M3.

## Consequences

- One tool for SQL, tests, docs and lineage; agents learn one framework.

## Options considered

- Plain SQL files run by our own Python script: we would rebuild ordering, tests, docs and lineage ourselves.
