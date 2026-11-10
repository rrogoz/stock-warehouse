# Agent instructions

Stock Warehouse is an agentic delivery demonstrator. AI agents take Jira stories (project `SW`) to PROD on a medallion warehouse (bronze, silver, gold in DuckDB, built with dbt) for public financial market data.

This file links to the docs and never copies them (ADR-009). When a doc and this file disagree, the doc wins.

## Read first

| Doc | Read when |
| --- | --- |
| [docs/overview.md](docs/overview.md) | starting work: goal, delivery workflow, milestones |
| [docs/principles.md](docs/principles.md) | designing or reviewing any change |
| [docs/adr/README.md](docs/adr/README.md) | before changing architecture or revisiting a past choice |
| [docs/glossary.md](docs/glossary.md) | a domain term is unclear |
| [docs/standards/](docs/standards/) | the change touches the area a standard covers |
| [docs/specs/](docs/specs/) | implementing a story: its approved spec |
| [README.md](README.md) | layout, setup, and the check commands to run before a pull request |

## Rules that are easy to miss

- **Data never lives in the repository.** Bronze, silver and gold are in object storage (ADR-003); `*.duckdb` and `*.parquet` are gitignored.
- **Secrets:** DEV values only, in a gitignored `.env` copied from `.env.example`. PROD secrets exist only in GitHub environments; agents never have PROD access or PROD data (ADR-002, ADR-008).
- **One story per pull request.** The story key is in the branch (`SW-12-short-title`), the commit and the PR title, which is a Conventional Commits line: `feat(connectors): add NBP connector [SW-12]`. Squash merge (ADR-009).
- **Stay inside the ADRs.** A change that contradicts an accepted ADR needs a new or superseding ADR in the same story, not a silent deviation.
- **Docs change with the code.** Every layer, entity and source has a documented place; update it in the same pull request.
- **Jira status is never a gate.** Gates are enforced in GitHub (ADR-010).
