---
name: standard-naming
description: Use when naming anything in Stock Warehouse (schema, table, column, entity or source config, connector, file, branch) or reviewing names in a change.
---

# Naming standard

The rules live in [docs/standards/naming.md](../../../docs/standards/naming.md). Read it before you name anything; it wins over this skill.

1. Pick the entity prefix and column suffix the standard gives for the kind and type.
2. Reuse an existing name for an existing concept: search the glossary, entity configs and dbt models first.
3. A new business name gets a [glossary](../../../docs/glossary.md) entry in the same change.
4. Source column names stay in bronze and staging; map them in the source config.
5. Instruments use their permanent code from the register, never a source ticker.
