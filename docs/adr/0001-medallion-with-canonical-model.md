# ADR-001: Medallion with a canonical model

- **Status:** Accepted
- **Date:** 2026-10-23

## Context

Today a change of data source forces a change of the data model. The platform must add instruments, asset classes and sources without rebuilding the model (see the requirements in the [overview](../overview.md#requirements)), and agents need clear boundaries to stay within.

## Decision

- **Three layers.** Bronze holds raw data per source, silver holds canonical entities, gold holds features and data products.
- **Canonical model in long format.** An instrument is a row, never a table or a column.
- **Anti-corruption layer** between sources and silver: each connector translates its source into the canonical contract, so no source detail leaks into silver or gold.
- **Own instrument identity**, independent of any source's symbols.

The individual rules are D2 to D14 in [principles](../principles.md).

## Consequences

- Adding an instrument is configuration; adding a source is a connector plus configuration.
- Every source must be mapped to the canonical contract before its data reaches silver.
- Gold and Stage 2 depend only on silver, so a source switch never reaches them.

## Options considered

- One table per instrument: N tables, unions everywhere, N migrations (rejected in D4).
- Source data used directly in gold: ties every product to one provider.
