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
| `.github/` | workflows (checks, agents), their scripts (checks, agent limits, Jira script, consistency check, metrics report), the pull request template and code owners |
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

The description follows the [pull request template](.github/pull_request_template.md). The four checks are required on main, with an approval and code owners ([`.github/CODEOWNERS`](.github/CODEOWNERS)); the settings are in the [switch on protection](docs/runbooks/switch-on-protection.md) runbook.

| Workflow | When | Does |
| --- | --- | --- |
| `consistency` | daily, 06:00 UTC | fails when a story is In progress without a spec on main, Done without a merged and released pull request, or the last weekday's PROD run (`prod-run.yml`, from M1) did not succeed ([ADR-010](docs/adr/0010-tracker-and-story-workflow.md)); `bootstrap` stories are exempt |
| `story-status` | a change pull request opens or merges | moves its story to In review or Awaiting release through the Jira script with role `ci`; spec pull requests move nothing; not a required check ([ADR-010](docs/adr/0010-tracker-and-story-workflow.md)) |
| `metrics` | Mondays, 07:00 UTC | per story merged in the last 7 days: review rounds and time from Ready to merge, in the job summary; the other metrics arrive in M1 |

## Agents

Each role is a one-click workflow (`agent-refine`, `agent-spec`, `agent-implement`, `agent-review`, `agent-fix`) on Rafal's Claude subscription ([ADR-011](docs/adr/0011-agent-orchestration.md)). `agent.yml` runs the builder roles as the Claude GitHub App; the review agent reads the change with a read-only token and its verdict is posted as `rrogoz-sw-review`. Before every run `.github/scripts/agent_prepare.py` enforces the limits: pause switch `SW_AGENTS_PAUSED`, main only, spec on main for implementation, at most three review rounds. Models, turn and time limits per role, and how to start or pause: [run an agent](docs/runbooks/run-an-agent.md).

## Jira script

Agents, CI and the planning assistant reach Jira only through `.github/scripts/jira.py` ([ADR-011](docs/adr/0011-agent-orchestration.md)). It uses the agent account from the `JIRA_*` settings, and each role may move a story only to the states ADR-010 gives it.

```sh
python3 .github/scripts/jira.py get SW-12
python3 .github/scripts/jira.py comment SW-12 --role refine --body "..."  # posted as "[refinement] ..."
python3 .github/scripts/jira.py verdict SW-12 --verdict ready --reason "..."  # dropdown "Refinement verdict" and paragraph "Verdict reason"
python3 .github/scripts/jira.py move SW-12 "Ready" --role refine
python3 .github/scripts/jira.py push stories.json --role plan  # create, or update Backlog stories
```

## Work

Stories live in Jira (project SW). One story per pull request; the title is a Conventional Commits line with the story key, for example `feat(connectors): add NBP connector [SW-12]`.
