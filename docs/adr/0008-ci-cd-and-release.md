# ADR-008: CI/CD and release

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

Agents deliver changes; Rafal's gates must be enforced by GitHub, not by trust. Builds on [ADR-002](0002-runtime-and-environments.md) (environments `prod-release` and `prod-run`, pre-release check).

## Decision

- **Automatic merge** when every required check passes and the review agent approves. The author can never approve its own change.
- **Rafal's gates enforced by code owners:** Rafal owns ADRs, standards, the instrument register, source selection config and workflow files. A change touching them cannot merge without his approval.
- **Main is protected for everyone, Rafal included:** pull requests only, required checks and approval, no force pushes, no bypass. One narrow exception, for changes to workflow files: [ADR-012](0012-workflow-file-changes.md).
- **Checks on every change,** all required: format, lint, types; unit and connector contract tests; config schema validation; dbt build on fixtures in full and incremental mode, with full-equals-incremental, replay and data tests; layer boundary check; secret scan and no-real-data check; Docker image build. Target: under 10 minutes.
- **A release candidate per merge:** every merge builds an image in GitHub Container Registry, tagged with date and short commit, and runs the pre-release check on it. Rafal approves on `prod-release` whenever he likes, and may skip to the latest candidate. Approval pins that tag as the PROD version; release notes come from the merged changes and their story keys.
- **Rollback:** approve the previous release again. For data, switch the pointer back (14 versions kept, [ADR-003](0003-storage-and-physical-format.md)) or rebuild from bronze.
- **Agents kept out of PROD:** PROD secrets exist only in the two environments, which accept runs from main only; Rafal is the only reviewer on `prod-release`; agent identities are not admins.
- **Public repository safety:** workflows from outside contributors need Rafal's approval and never see secrets; secret scanning and push protection are on.

## Consequences

- Rafal is not a bottleneck on ordinary changes (from M2; supervised mode in M1, [ADR-011](0011-agent-orchestration.md)).

## Options considered

- Rafal merges every change: bottleneck, and the demo shows less autonomy.
- Releases in batches started by Rafal: bigger batches, problems found later.
