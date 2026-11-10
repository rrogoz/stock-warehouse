# Architecture decisions

One file per decision. A new or changed ADR needs Rafal's approval (gate 2). Use the [template](../templates/adr.md); statuses are `Proposed`, `Accepted`, `Superseded by ADR-NNN`.

| ADR | Decision | Status |
| --- | --- | --- |
| [ADR-001](0001-medallion-with-canonical-model.md) | Medallion with a canonical model | Accepted |
| [ADR-002](0002-runtime-and-environments.md) | Runtime and environments | Accepted |
| [ADR-003](0003-storage-and-physical-format.md) | Storage and physical format | Accepted |
| [ADR-004](0004-physical-data-model.md) | Physical data model | Accepted |
| [ADR-005](0005-sources-and-ingestion.md) | Sources and ingestion | Accepted |
| [ADR-006](0006-transformation-and-data-testing.md) | Transformation and data testing | Accepted |
| [ADR-007](0007-pipeline-engine-and-operations.md) | Pipeline engine, orchestration and operations | Accepted |
| [ADR-008](0008-ci-cd-and-release.md) | CI/CD and release | Accepted |
| [ADR-009](0009-repository-and-standards.md) | Repository and concrete standards | Accepted |
| [ADR-010](0010-tracker-and-story-workflow.md) | Tracker and story workflow | Accepted |
| [ADR-011](0011-agent-orchestration.md) | Agent orchestration | Accepted |
| [ADR-012](0012-workflow-file-changes.md) | Workflow file changes | Accepted |

**Ground rules for every ADR.** A choice that breaks one needs an exception Rafal approves.

- Zero cost to start: free tools and free public sources.
- Portability: runs on any host without code changes.
- Public repository: no market data or secrets in it.
- Agents never touch PROD, enforced technically, not only by instruction.
- Every standard is checkable, by an automated check or by the review agent.
- The [principles](../principles.md) hold, and the Stage 2 requirements in the [overview](../overview.md#stage-2-requirements) are supported.
