# Stock Warehouse

An agentic delivery demonstrator: AI agents take work from a Jira story to PROD on a small data warehouse for public financial market data (bronze, silver, gold in DuckDB).

Status: M0 Foundations. Start with the [overview](docs/overview.md), then [principles](docs/principles.md), [decisions](docs/adr/README.md) and the [glossary](docs/glossary.md).

## Layout

| Folder | Holds |
| --- | --- |
| `docs/` | overview, principles, glossary, `adr/`, `standards/`, `specs/`, `runbooks/`, `templates/` |
| `src/engine/` | the pipeline command and its steps |
| `src/connectors/` | one module per source: fetch and parse |
| `config/` | `sources/`, `entities/` (YAML) and `schemas/` that validate them |
| `reference/` | instrument register, calendars |
| `dbt/` | macros, staging, silver, gold, tests |
| `tests/` | `unit/`, `contract/`, `integration/`, `fixtures/` |
| `.github/` | CI workflows, their check scripts and the pull request template |
| `.claude/skills/` | agent skills: one per role, one per standard ([ADR-011](docs/adr/0011-agent-orchestration.md)) |

Code only: data never lives in this repository.

## Run locally

Needs [uv](https://docs.astral.sh/uv/). It installs Python 3.12 and the tools.

```sh
uv sync                      # install
cp .env.example .env         # fill in DEV values only
uv run ruff format --check . # format
uv run ruff check .          # lint
uv run mypy                  # types
uv run pytest                # tests
uv run sqlfluff lint dbt     # SQL style
uv run mypy .github/scripts  # types of the check scripts
python3 .github/scripts/check_docs.py          # links, template sections, ADR statuses
python3 .github/scripts/check_no_real_data.py  # no data files in the repository
```

With Docker, the same image runs in DEV and PROD; only configuration differs:

```sh
docker build -t stock-warehouse .
docker run --rm --env-file .env stock-warehouse
```

## Checks

CI runs on every pull request and on main ([ADR-008](docs/adr/0008-ci-cd-and-release.md)). Each check enforces a rule in a [standard](docs/standards/README.md).

| Workflow, job | Checks |
| --- | --- |
| `ci`, code | Ruff format and lint, mypy, pytest, SQLFluff |
| `ci`, repository | docs check, no-real-data check, gitleaks secret scan of the whole history |
| `ci`, docker | the image builds and runs |
| `change`, change conventions | title, branch and description follow the [change conventions](docs/standards/change-conventions.md) |

The description follows the [pull request template](.github/pull_request_template.md). Making the checks required is SW-9.

## Work

Stories live in Jira (project SW). One story per pull request; the title is a Conventional Commits line with the story key, for example `feat(connectors): add NBP connector [SW-12]`.
