# ADR-009: Repository and concrete standards

- **Status:** Accepted
- **Date:** 2026-10-27

## Context

Agents and people need one source of truth that is short and easy to read. Builds on [ADR-004](0004-physical-data-model.md) (naming), [ADR-007](0007-pipeline-engine-and-operations.md) and [ADR-008](0008-ci-cd-and-release.md) (CI checks).

## Decision

**Tooling and layout**

- **Python:** uv, Ruff (format and lint), mypy, pytest. SQLFluff for SQL in gold and macros.
- **Configs are YAML** (comments allowed), each validated by a JSON Schema in CI.
- **Layout:** as in the [README](../../README.md#layout). Agent instructions and skills: [ADR-011](0011-agent-orchestration.md).
- **Naming beyond ADR-004:** connectors and configs are named after the source or entity (`nbp`, `fact_price_daily`); ADR files `NNNN-short-title.md`; branches `<story key>-short-title`.
- **Changes:** one story per pull request; the title is a Conventional Commits line with the story key, for example `feat(connectors): add NBP connector [SW-12]`; squash merge.
- **Change template:** story and spec links, what, why, how it was tested, which docs changed, Definition of Done checklist.
- **Checked in CI:** formatting, lint, types, SQL style; config schemas; ADR-004 naming; layer boundaries; every entity and field documented; change template filled and story key present; no real data or secrets.
- **Checked by the review agent:** meaningful business names, used consistently; small focused change (guide: under about 400 changed lines, excluding fixtures and generated files); meaningful docs; a bug fix adds a test; the change follows its spec and the standards.
- **One skill per standard:** each file in `docs/standards/` has a matching agent skill.

**Documentation**

Docs live in the repository, reviewed in the same pull request. Jira holds the work, not the documentation. Each fact has one home; everything else links to it.

| Fact | Lives in |
| --- | --- |
| Goal, scope, milestones, requirements | [overview.md](../overview.md) |
| Principles | [principles.md](../principles.md) |
| Decisions | `docs/adr/` |
| How we work: standards, workflow, gates | `docs/standards/`; agent instructions link, never copy |
| What an entity or source is | its config file, shown in the dbt docs |
| Business terms | [glossary.md](../glossary.md) |
| How to operate | `docs/runbooks/` |
| What to do next: priority, status, acceptance criteria | the Jira story |
| How one story is built | its spec in `docs/specs/` |
| What changed and when | pull requests and release notes |

- **Conflict rule:** the repository wins on how the system works; Jira wins on what to do and when. Docs that disagree with the code are a bug.
- **A spec records one change, not the system.** Before a story merges, everything lasting in its spec moves into docs or config; the spec is then frozen.
- **Writing rules:** the first line says what the document is for; plain words, short sentences, active voice; each term defined once, in the glossary; bullets and tables over paragraphs; one example per rule, from this project; link, never copy; README, each standard and each ADR up to one page, a spec up to two, a runbook is numbered steps only; diagrams in Mermaid; English only.
- **Fixed templates** in [templates/](../templates/): ADR, spec, runbook, standard.
- **Kept true automatically:** CI checks docs coverage, links, template sections and ADR statuses; the review agent checks that a change updates every doc it affects.

## Consequences

- Agents and people read one short set of docs in the repository; Jira holds only the work.
- Docs are reviewed with the code, so a change costs a little more review, and drift shows up as a failing check or a review finding.
- Every rule marked "checked in CI" needs a check; until one exists, the review agent covers it.

## Options considered

- pip, black, flake8, isort: more tools for the same job, slower.
- JSON configs: no comments, a second format next to dbt's YAML.
- Confluence for docs: drifts from the code, not reviewed with it.
