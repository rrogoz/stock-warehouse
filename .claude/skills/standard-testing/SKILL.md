---
name: standard-testing
description: Use when writing or reviewing tests, fixtures or data tests for an entity, layer, connector or bug fix in Stock Warehouse.
---

# Testing standard

The rules live in [docs/standards/testing.md](../../../docs/standards/testing.md). Read it first; it wins over this skill.

1. List the tests the standard requires for each entity, layer and connector the change touches, and write each one.
2. Fixtures are synthetic, in `tests/fixtures/`. Never copy real market data and never call a real source.
3. A bug fix starts with a test that fails without the fix.
4. Run the checks in the [README](../../../README.md#run-locally) before you hand over; all must pass.
