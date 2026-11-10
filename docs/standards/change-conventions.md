# Standard: Change conventions

One page at most. Skill: `standard-change-conventions`.

## Purpose

Every change is small, traceable to one story, checked by tools and reviewed by someone other than its author ([requirements](../principles.md#what-standards-must-guarantee), [ADR-008](../adr/0008-ci-cd-and-release.md), [ADR-009](../adr/0009-repository-and-standards.md)).

## Rules

- **One story per pull request.** The story key is in the branch, every commit and the title.
- **Title** is a Conventional Commits line with the key: `type(scope): summary [SW-NNN]`. Types: `feat`, `fix`, `docs`, `test`, `refactor`, `chore`, `ci`.
- **Description** follows the change template: story and spec links, what, why, how it was tested, which docs changed, Definition of Done checklist.
- **Small and focused:** guide under about 400 changed lines, excluding fixtures and generated files. Bigger work is split into stories.
- **Code style is the tools' config,** not prose: Ruff (format and lint), mypy strict and SQLFluff as set in `pyproject.toml`. Every change passes them unchanged; a rule is relaxed only in that file, with a comment.
- **No secrets and no real data** in any commit. DEV values go in a gitignored `.env`.
- **Review:** nothing reaches main without approval, and the reviewer is never the author. Changes to ADRs, standards, the register, source selection and workflows need Rafal (code owners).
- **Squash merge;** the branch is up to date with main before merge.

## Example

Branch `SW-12-nbp-connector`, title `feat(connectors): add NBP connector [SW-12]`, description linking SW-12 and `docs/specs/SW-12.md`, tested by `tests/contract/test_nbp.py`, docs changed: `config/sources/nbp.yaml`.

## How it is checked

| Rule | Check | When |
| --- | --- | --- |
| Story key in branch and title; Conventional Commits title | CI change check | SW-7 |
| Change template filled | CI change check | SW-7 |
| Format, lint, types, SQL style | CI: Ruff, mypy, SQLFluff | SW-7 |
| No secrets, no real data | CI secret scan and no-real-data check; GitHub push protection | SW-7 |
| Approval by someone other than the author; code owners | Branch protection and CODEOWNERS | SW-9 |
| Small and focused | Review agent | SW-9 |
