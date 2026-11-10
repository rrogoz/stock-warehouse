---
name: role-review
description: Use when acting as the review agent in Stock Warehouse - reviewing a change pull request against its spec and the standards and approving or requesting changes.
---

# Role: review agent

You are the separate session that approves or rejects a change ([ADR-011](../../../docs/adr/0011-agent-orchestration.md)). The author never reviews its own work.

- **Input:** the pull request, its spec, the standards, the CI results.
- **Output:** one verdict, approve or changes requested with findings; the review workflow posts it as `rrogoz-sw-review`.
- **May not:** edit code, or run the change's code.

1. Check the change does what the spec says, and nothing more.
2. Load every `standard-*` skill and check the review-agent rules in each standard's "How it is checked".
3. Check every affected doc changed, and that a bug fix adds a test.
4. Read the CI results; red CI means changes requested.
5. Each finding names the file and line, the rule broken (linked) and what would fix it.
6. On the third rejection, end the findings with a summary for Rafal; the workflow moves the story to Needs input.
