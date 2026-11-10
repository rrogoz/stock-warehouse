# Principles

The architecture rules every change must keep, and what each standard must guarantee. The overall direction is [ADR-001](adr/0001-medallion-with-canonical-model.md); how each rule is built is in the ADR it links. Changing a principle needs a new ADR and Rafal's approval.

## Architecture principles

| # | Principle | Why | Built in |
| --- | --- | --- | --- |
| D2 | Bronze holds raw data per source and endpoint, append-only, with load metadata | Full replay without downloading again | [ADR-003](adr/0003-storage-and-physical-format.md) |
| D3 | Silver holds canonical entities, independent of source and asset class | Scale through configuration, not model changes | [ADR-004](adr/0004-physical-data-model.md) |
| D4 | One table per entity, never one per instrument | Per-instrument tables mean N tables, a union in every cross-section query, N migrations and many small files | [ADR-004](adr/0004-physical-data-model.md) |
| D5 | Gold holds features, labels and business products, and reads only from silver | A clear layer boundary for agents | [ADR-006](adr/0006-transformation-and-data-testing.md) |
| D6 | Own instrument identity: a permanent code that never changes, plus a current symbol following one naming convention per asset class. Each connector translates its symbols into it. An identity change (for example a rename) is an approved reference-data change, and reference data keeps its history | A symbol or source change does not change identity | [ADR-004](adr/0004-physical-data-model.md) |
| D7 | Every price series records its adjustment basis (raw, split-adjusted, total return) and bases are never mixed. Target: raw prices plus corporate events, adjustments derived by us. History from an adjusted source is labelled as such | Independence from each provider's adjustment method | [ADR-004](adr/0004-physical-data-model.md), [ADR-005](adr/0005-sources-and-ingestion.md) |
| D8 | Which source supplies which data is configuration, not code; several sources may coexist, and every silver record knows its source | Switching source is a configuration change | [ADR-007](adr/0007-pipeline-engine-and-operations.md) |
| D9 | A new source is reconciled against the current one before switching; every connector passes the canonical contract; switching the primary source is Rafal's gate | Controlled source migration | [ADR-005](adr/0005-sources-and-ingestion.md) (designed at M4) |
| D10 | Storage is partitioned by source, endpoint and load date, never by instrument | Instruments are rows, not files | [ADR-003](adr/0003-storage-and-physical-format.md) |
| D11 | Features and labels are point in time: nothing known after their as-of date is used | No look-ahead in Stage 2 | [ADR-004](adr/0004-physical-data-model.md), [ADR-006](adr/0006-transformation-and-data-testing.md) |
| D13 | Every record keeps two times: the date it describes and when we learned it. Nothing is overwritten; corrections are new records. History from an adjusted source is marked as not point in time before its capture date | Point-in-time data, append-only history and replay cannot be added later for data already overwritten | [ADR-004](adr/0004-physical-data-model.md) |
| D14 | Trading calendar and quote status (traded, suspended, missing on our side) are first-class reference data. A session counts as loaded only when every expected instrument is accounted for | The daily load must tell a holiday from a failed download | [ADR-005](adr/0005-sources-and-ingestion.md), [ADR-006](adr/0006-transformation-and-data-testing.md) |

D1 (the stack) became ADR-002 to ADR-006. D12 is a Stage 2 design rule and is not part of Stage 1.

## What standards must guarantee

The concrete rules live in [standards/](standards/). Each must meet the requirements below, be checkable by a test or by the review agent, and map to at least one agent skill.

**Naming**

- One documented convention per kind of object: layer, entity, field, source.
- A name tells the layer and the kind of entity (fact, dimension, reference).
- From silver up, names are business names; source names appear only in bronze.
- The same concept has the same name in every layer.
- Units and currency are explicit in the name or in metadata.

**Data modelling**

- Every entity declares its grain and key.
- A new instrument or asset class adds rows, never tables or columns (D3, D4).
- Every record carries lineage: source, load run, business date and knowledge time (D8, D13).
- Every price series carries its adjustment basis (D7).
- Silver follows the canonical contract; source-specific fields stay in bronze.
- Schema changes are additive by default; a breaking change needs an ADR.

**Layer boundaries**

- Bronze reads only sources, silver reads only bronze and reference data, gold reads only silver (D5).
- External producers enter only through bronze.
- Gold features never depend on signals or portfolios.
- Violations are detected automatically, not only in review.

**Testing**

- Every entity is tested for key uniqueness, required fields and its own business rules.
- Each layer has its own checks: bronze for load completeness, silver for the contract and session continuity against the calendar (D14), gold for value ranges and no look-ahead.
- Every connector has a contract test (D9).
- All tests run on synthetic fixtures, without real data.
- Every bug fix adds a test that would have caught it.
- A failing test blocks promotion to the next environment.

**Documentation**

- Every entity is documented: purpose, grain, key, fields with meaning and units, lineage.
- Documentation lives with the code and changes in the same change.
- Decisions are ADRs with context, decision, consequences and status.
- Documentation is structured enough for the refinement agent to check a story against it.

**Change conventions**

- One story per change; the change links its story and spec.
- The description says what, why, how it was tested and which docs changed.
- Nothing reaches main without review, and the reviewer is never the author.
- Changes are small and focused.
