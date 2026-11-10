---
name: standard-layer-boundaries
description: Use when writing or reviewing a connector, dbt model or anything that reads data across bronze, staging, silver and gold in Stock Warehouse.
---

# Layer boundaries standard

The rules live in [docs/standards/layer-boundaries.md](../../../docs/standards/layer-boundaries.md). Read it first; it wins over this skill.

1. Before adding a read, check the standard allows that layer to read the one you need.
2. Use `ref()` for models and `source()` for bronze; never a hard-coded schema name.
3. Put each model in the folder of its layer.
4. If the data you need is not in the allowed layer, add it there first (or ask in the story); never skip a layer.
