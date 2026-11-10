# ADR-010: Tracker and story workflow

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

Work needs a tracker that matches the delivery workflow in the [overview](../overview.md#delivery-workflow), at zero cost. Builds on [ADR-008](0008-ci-cd-and-release.md) and [ADR-009](0009-repository-and-standards.md).

## Decision

- **Jira Free, one Kanban project, key `SW`,** because it is the tool used at work. Milestones give the rhythm. Issue types: Epic (one per milestone), Story, Bug, Spike. No sub-tasks: one story is one change.
- **Jira status is never a gate.** On the free plan everyone is an admin and there is no audit log, so gates are enforced in GitHub. Agents and CI move stories through the API, and a daily consistency check catches drift.
- **Workflow states:**

| State | Means | Moved in by |
| --- | --- | --- |
| Backlog | Not yet refined | Rafal |
| Refinement | The refinement agent is checking it | Rafal, picking what comes next |
| Needs input | Questions or a split proposal wait for Rafal | Refinement agent |
| Ready | Definition of Ready met | Refinement agent |
| Spec review | Spec written, waiting for Rafal's approval | Spec agent |
| In progress | Spec approved; implementation running | Rafal's spec approval |
| In review | Pull request open; the review agent is working | CI, when the pull request opens |
| Awaiting release | Merged; release candidate built and checked | CI, on merge |
| Done | Released to PROD | CI, when Rafal approves the release |

- **Story template (Definition of Ready fields):** what and why in two or three lines; epic; testable acceptance criteria; architecture elements touched, as labels (layer, entity, source); data contract, or "defining it is this story"; dependencies as Jira links; out of scope. The refinement verdict and reason go in a custom field.
- **Links:** the story key is in the branch name, pull request title and commit. The GitHub for Jira app shows branches, pull requests, builds and deployments on the story.
- **Metrics without bookkeeping:** a weekly CI script reads Jira and GitHub history and reports per story: review rounds; time from Ready to merge; Rafal's actions outside his gates, by step; refinement verdict against outcome (scoring rule set at M1).
- **Consistency check:** a daily CI job compares Jira with GitHub (In progress needs an approved spec, Done needs a released change) and confirms the last weekday's PROD run succeeded. A mismatch fails the job, so GitHub emails Rafal.
- **Site ownership:** Rafal is the Jira site admin; daily agent and CI activity keeps the free site active.

## Consequences

- Jira can drift without blocking anything; the daily consistency check is what keeps it true.
- Statuses move without bookkeeping, so the metrics come from Jira and GitHub history.

## Options considered

- GitHub Issues and Projects: next to the code, but not the tool used at work.
- Scrum sprints: ceremonies with nobody to attend them.
