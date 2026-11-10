"""Weekly metrics report: per story, from Jira and GitHub history (ADR-010, overview Metrics).

Skeleton: covers stories whose pull request merged in the last 7 days and reports
review rounds and time from Ready to merge. Interventions outside the gates and
verdict accuracy show "not measured yet" until M1 sets how to score them.
Bootstrap (M0) stories are left out. Writes Markdown to stdout and, in CI, to
the job summary.
"""

from __future__ import annotations

import os
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from github_api import GitHub, parse_time  # noqa: E402
from jira import Jira  # noqa: E402

DAYS = 7
NOT_YET = "not measured yet"
HEADER = (
    "| Story | Pull request | Review rounds | Ready to merge | Interventions | Verdict |\n"
    "| --- | --- | --- | --- | --- | --- |"
)


def ready_at(changelog: list[Any]) -> datetime | None:
    """When the story first moved to Ready."""
    for entry in changelog:
        for item in entry.get("items", []):
            if item.get("field") == "status" and item.get("toString") == "Ready":
                return parse_time(entry["created"])
    return None


def duration(start: datetime | None, end: datetime) -> str:
    if start is None:
        return "never Ready"
    hours = (end - start).total_seconds() / 3600
    return f"{hours / 24:.1f} days" if hours >= 24 else f"{hours:.1f} hours"


def row(key: str, pull: dict[str, Any], rounds: int, ready: datetime | None) -> str:
    merged = parse_time(pull["merged_at"])
    link = f"[#{pull['number']}]({pull['html_url']})"
    return f"| {key} | {link} | {rounds} | {duration(ready, merged)} | {NOT_YET} | {NOT_YET} |"


def report(rows: list[str], since: datetime) -> str:
    title = f"## Metrics, stories merged since {since:%Y-%m-%d}\n"
    if not rows:
        return title + "\nNo stories merged in this window.\n"
    return "\n".join([title, HEADER, *rows]) + "\n"


def main() -> int:
    since = datetime.now(UTC) - timedelta(days=DAYS)
    jira, github = Jira.from_env(), GitHub.from_env()
    rows: list[str] = []
    for key, pull in sorted(github.merged_pulls().items()):
        if parse_time(pull["merged_at"]) < since:
            continue
        if "bootstrap" in jira.issue(key, "labels")["fields"].get("labels", []):
            continue
        rounds = github.changes_requested(pull["number"])
        rows.append(row(key, pull, rounds, ready_at(jira.changelog(key))))
    text = report(rows, since)
    print(text)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main())
