# ADR-012: Workflow file changes

- **Status:** Accepted
- **Date:** 2026-11-10

## Context

Builder agents push as the Claude GitHub App ([ADR-011](0011-agent-orchestration.md)). GitHub refuses any app push that creates or changes a file in `.github/workflows/` unless the app has the workflows permission, and the Claude app does not have it (found in SW-15). [ADR-008](0008-ci-cd-and-release.md) allows no bypass of main's protection, so such a change could not land at all.

## Decision

- **A narrow exception to two ADRs,** only for a change that touches `.github/workflows/`: to "no bypass" in [ADR-008](0008-ci-cd-and-release.md), and to [ADR-011](0011-agent-orchestration.md), where the implementation agent builds every change and the planning assistant only plans. Every other change follows both unchanged.
- **The story keeps the normal flow** up to the code: refinement, spec, and Rafal's spec approval.
- **The planning assistant, not the implementation agent, builds the change** from the approved spec on a `SW-NNN-…` branch and opens it as an ordinary pull request; the pull request description says so.
- **Required before merge:** all required checks green and an approval from the review agent (`agent-review`), as for any change.
- **Rafal merges with the ruleset bypass,** which only the Repository admin role has. Workflow files are his code-owner gate anyway ([ADR-008](0008-ci-cd-and-release.md)).

## Consequences

- Workflow changes can land; the review agent still checks them against the spec and standards.
- These stories' metrics count no implementation agent run; the pull request description says the change was built in a planning session.
- A bypass merge is visible in the pull request and the ruleset insights; the daily consistency check is unchanged.

## Options considered

- Own builder GitHub App with the workflows permission: fully agent-built, but one more identity and private key to keep; not worth it for rare workflow changes.
- A personal access token with the workflow scope for agents: a long-lived credential tied to a person, against least privilege ([ADR-011](0011-agent-orchestration.md)).
- No exception: workflow fixes found by agents could never merge.

**Revisit if** workflow changes become frequent, or the Claude GitHub App gains the workflows permission.
