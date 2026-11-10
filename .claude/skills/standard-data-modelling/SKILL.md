---
name: standard-data-modelling
description: Use when adding or changing an entity, its grain, keys, columns or contract in Stock Warehouse, or reviewing such a change.
---

# Data modelling standard

The rules live in [docs/standards/data-modelling.md](../../../docs/standards/data-modelling.md), built on [ADR-004](../../../docs/adr/0004-physical-data-model.md). Read both first; they win over this skill.

1. Write the grain as one sentence and name the business key before writing any SQL or config.
2. A new instrument or asset class adds rows and register entries, never tables or columns.
3. Keep silver insert-only, on business keys, with the standard columns; technical keys only in gold.
4. Removing, renaming or retyping a field is breaking: stop and propose an ADR and a new contract version.
