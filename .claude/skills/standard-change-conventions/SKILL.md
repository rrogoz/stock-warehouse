---
name: standard-change-conventions
description: Use when creating a branch, commit or pull request in Stock Warehouse, or reviewing one against the change rules.
---

# Change conventions standard

The rules live in [docs/standards/change-conventions.md](../../../docs/standards/change-conventions.md). Read it first; it wins over this skill.

1. One story per change: branch `<story key>-short-title`, the key in every commit and in the title.
2. Title: `type(scope): summary [SW-NNN]`; description on the change template.
3. Run the checks in the [README](../../../README.md#run-locally); fix the code, never the tool config, unless the change says why.
4. Check no secret and no real data is staged before you commit.
5. Keep it under about 400 changed lines; if it grows, stop and propose a split.
