# Stock Warehouse

An agentic delivery demonstrator: AI agents take work from a Jira story to PROD on a small data warehouse for public financial market data (bronze, silver, gold in DuckDB).

Status: M0 Foundations. Goal, scope and decisions move into `docs/` in the next M0 story.

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
```

With Docker, the same image runs in DEV and PROD; only configuration differs:

```sh
docker build -t stock-warehouse .
docker run --rm --env-file .env stock-warehouse
```

## Work

Stories live in Jira (project SW). One story per pull request; the title is a Conventional Commits line with the story key, for example `feat(connectors): add NBP connector [SW-12]`.
