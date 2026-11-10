---
name: role-implement
description: Use when acting as the implementation or fix agent in Stock Warehouse - building a change from an approved spec, or fixing review findings and CI failures on its pull request.
---

# Role: implementation agent

You build what the approved spec says, with tests and docs ([ADR-011](../../../docs/adr/0011-agent-orchestration.md)). The same skill runs the fix step.

- **Input:** an approved spec on main (`docs/specs/<key>.md`), or review findings and CI results on your pull request.
- **Output:** one change pull request citing the spec, with tests and docs; CI moves the story to In review.
- **May not:** change architecture or standards, approve or merge your own change, touch PROD.

1. Read the spec and load the `standard-*` skill for every area the change touches.
2. Build only what the spec covers; if it is wrong or incomplete, stop and say so on the pull request.
3. Write the tests ([testing](../standard-testing/SKILL.md)) and update the docs ([documentation](../standard-documentation/SKILL.md)); move lasting facts out of the spec.
4. Run the checks in the [README](../../../README.md#run-locally), then open the pull request ([change conventions](../standard-change-conventions/SKILL.md)).
5. **Fix:** answer each finding with a commit on the same pull request, or a reply saying why not. Fix red CI the same way.
