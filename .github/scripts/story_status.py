"""Story status: CI moves a story when its change pull request opens or merges (ADR-010).

Runs from main on pull_request_target. Reads PR_ACTION, PR_MERGED and PR_TITLE from
the environment (never interpolated) and the JIRA_* settings. Opened or reopened
moves the story to In review; merged moves it to Awaiting release. Spec pull
requests and titles without a story key move nothing. Not a required check:
Jira status is never a gate.

    PR_ACTION=opened PR_MERGED=false PR_TITLE="feat(x): y [SW-12]" \
        python3 .github/scripts/story_status.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from github_api import TITLE_KEY  # noqa: E402
from jira import Jira, JiraError  # noqa: E402

SPEC_PREFIX = "docs(specs)"


def target(action: str, merged: bool, title: str) -> tuple[str, str] | None:
    """The story and the state CI moves it to for this event, or None."""
    match = TITLE_KEY.search(title)
    if not match or title.startswith(SPEC_PREFIX):
        return None
    if action in ("opened", "reopened"):
        return match.group(1), "In review"
    if action == "closed" and merged:
        return match.group(1), "Awaiting release"
    return None


def apply(jira: Jira, key: str, status: str) -> str:
    """Move the story unless it is already there; return what happened."""
    current = str(jira.issue(key, "status")["fields"]["status"]["name"])
    if current.casefold() == status.casefold():
        return f"{key} is already {current}; nothing to do"
    jira.move(key, status, "ci")
    return f"{key}: {current} -> {status}"


def main() -> int:
    action = os.environ.get("PR_ACTION", "")
    merged = os.environ.get("PR_MERGED", "").strip().lower() == "true"
    title = os.environ.get("PR_TITLE", "")
    found = target(action, merged, title)
    if found is None:
        print(f"::notice::no story move for {action!r} on {title!r}")
        return 0
    try:
        print(apply(Jira.from_env(), *found))
    except JiraError as error:
        print(f"::error::story status: {error}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
