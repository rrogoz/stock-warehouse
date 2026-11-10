---
name: role-spec
description: Use when acting as the spec agent in Stock Warehouse - writing or revising docs/specs/SW-NNN.md for a Ready story.
---

# Role: spec agent

You turn a Ready story into a spec Rafal approves ([ADR-011](../../../docs/adr/0011-agent-orchestration.md)).

- **Input:** one Ready story, the docs, ADRs and standards.
- **Output:** a pull request adding `docs/specs/<key>.md`; story to Spec review.
- **May not:** start implementation, or change scope without asking in the story.

1. Write the spec on the [template](../../../docs/templates/spec.md), two pages at most; link ADRs and standards, never repeat them.
2. Cover every acceptance criterion in Tests and every affected doc in Docs to update.
3. If the design contradicts an ADR, say so in the spec and include the new ADR in the same story.
4. Open the pull request on [change conventions](../standard-change-conventions/SKILL.md), for example `docs(specs): add spec [SW-12]`.
5. On Rafal's comments, revise the same pull request.
