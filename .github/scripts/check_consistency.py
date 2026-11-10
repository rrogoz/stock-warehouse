"""Daily consistency check: Jira agrees with GitHub, and PROD ran (ADR-010, ADR-007).

Fails, so GitHub emails Rafal, when:
- a story is In progress without an approved spec (docs/specs/<key>.md on main);
- a story is Done without a merged pull request released to PROD after the merge;
- the last weekday's PROD run did not succeed (catches runs that never started).
Stories labelled bootstrap (M0) are exempt: they have no spec or release.
Run from a checkout of main, with the Jira and GitHub environment variables set.
"""

from __future__ import annotations

import sys
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_api import GitHub, parse_time  # noqa: E402
from jira import Jira  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
PROD_WORKFLOW = "prod-run.yml"
# labels != x leaves out unlabelled issues in JQL, hence the IS EMPTY.
JQL = (
    'project = SW AND status in ("In progress", "Done") '
    "AND (labels IS EMPTY OR labels != bootstrap)"
)


def last_weekday(today: date) -> date:
    """The most recent Monday to Friday before today."""
    day = today - timedelta(days=1)
    while day.weekday() >= 5:
        day -= timedelta(days=1)
    return day


def story_problems(
    stories: list[Any],
    specs: set[str],
    merged: dict[str, dict[str, Any]],
    released: datetime | None,
) -> list[str]:
    problems: list[str] = []
    for story in stories:
        key = story["key"]
        if "bootstrap" in story["fields"].get("labels", []):
            continue
        status = story["fields"]["status"]["name"]
        if status.casefold() == "in progress" and key not in specs:
            problems.append(f"{key} is In progress but docs/specs/{key}.md is not on main")
        if status.casefold() == "done":
            pull = merged.get(key)
            if pull is None:
                problems.append(
                    f"{key} is Done but no merged pull request has [{key}] in its title"
                )
            elif released is None or released < parse_time(pull["merged_at"]):
                problems.append(f"{key} is Done but #{pull['number']} is not released to PROD yet")
    return problems


def prod_run_problem(runs: list[Any] | None, today: date) -> str | None:
    if runs is None:
        print(f"{PROD_WORKFLOW} does not exist yet (M1); PROD run not checked")
        return None
    day = last_weekday(today)
    on_day = [run for run in runs if parse_time(run["created_at"]).date() == day]
    if not on_day:
        return f"no PROD run on {day}: the schedule did not start ({PROD_WORKFLOW})"
    if not any(run.get("conclusion") == "success" for run in on_day):
        return f"the PROD run on {day} did not succeed: {on_day[0]['html_url']}"
    return None


def main() -> int:
    today = datetime.now(UTC).date()
    jira, github = Jira.from_env(), GitHub.from_env()
    specs = {path.stem for path in (ROOT / "docs" / "specs").glob("SW-*.md")}
    stories = jira.search(JQL)
    needs_github = any(s["fields"]["status"]["name"].casefold() == "done" for s in stories)
    merged = github.merged_pulls() if needs_github else {}
    released = github.last_release() if needs_github else None
    problems = story_problems(stories, specs, merged, released)
    since = (last_weekday(today) - timedelta(days=1)).isoformat()
    run = prod_run_problem(github.workflow_runs(PROD_WORKFLOW, since), today)
    if run:
        problems.append(run)
    print(f"checked {len(stories)} stories and the PROD run of {last_weekday(today)}")
    for problem in problems:
        print(f"::error::{problem}")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
