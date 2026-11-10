"""Agent run check: refuse a run the limits of ADR-011 do not allow.

Runs before every agent. Refuses when the pause switch is on, the run is not
from main, the story or pull request is not valid for the role, an
implementation has no spec on main, or a pull request already had three
rejections. Writes story, pr, branch, sha and round to GITHUB_OUTPUT.

    python3 .github/scripts/agent_prepare.py --role implement --story SW-12
    python3 .github/scripts/agent_prepare.py --role review --pr 42
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any, Protocol

ROOT = Path(__file__).resolve().parents[2]
ROLES = ("refine", "spec", "implement", "fix", "review")
ON_PULL_REQUEST = ("fix", "review")
KEY = re.compile(r"^SW-\d+$")
TITLE_KEY = re.compile(r"\[(SW-\d+)\]\s*$")
MAX_REJECTIONS = 3  # ADR-011: at most three review rounds


class RefusedError(Exception):
    """The run is not allowed; the message says why."""


class PullRequests(Protocol):
    repository: str

    def get(self, path: str) -> Any: ...

    def changes_requested(self, number: int) -> int: ...


def prepare(
    role: str,
    story: str,
    pr: str,
    *,
    paused: bool,
    ref: str,
    github: PullRequests | None,
    root: Path = ROOT,
) -> dict[str, str]:
    if paused:
        raise RefusedError("agents are paused (repository variable SW_AGENTS_PAUSED is true)")
    if role not in ROLES:
        raise RefusedError(f"unknown role {role!r}")
    if ref != "refs/heads/main":
        raise RefusedError(f"agents run from main only, not {ref!r}")
    if role not in ON_PULL_REQUEST:
        if not KEY.match(story):
            raise RefusedError(f"{story!r} is not a story key, e.g. SW-12")
        if role == "implement" and not (root / "docs" / "specs" / f"{story}.md").is_file():
            raise RefusedError(f"no approved spec docs/specs/{story}.md on main")
        return {"story": story, "pr": "", "branch": "", "sha": "", "round": "1"}

    if not pr.isdigit() or github is None:
        raise RefusedError(f"{pr!r} is not a pull request number")
    pull = github.get(f"pulls/{pr}")
    if pull is None or pull["state"] != "open":
        raise RefusedError(f"pull request #{pr} is not open")
    if pull["head"]["repo"]["full_name"] != github.repository:
        raise RefusedError(f"pull request #{pr} comes from a fork; agents never run on it")
    match = TITLE_KEY.search(pull["title"])
    if not match:
        raise RefusedError(f"pull request #{pr} has no story key in its title")
    rejections = github.changes_requested(int(pr))
    if rejections >= MAX_REJECTIONS:
        raise RefusedError(
            f"pull request #{pr} was rejected {rejections} times; the story waits for Rafal"
        )
    return {
        "story": match.group(1),
        "pr": pr,
        "branch": pull["head"]["ref"],
        "sha": pull["head"]["sha"],
        "round": str(rejections + 1),
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--role", required=True)
    parser.add_argument("--story", default="")
    parser.add_argument("--pr", default="")
    args = parser.parse_args(argv)

    github = None
    if args.role in ON_PULL_REQUEST:
        sys.path.insert(0, str(Path(__file__).parent))
        from github_api import GitHub

        github = GitHub.from_env()
    try:
        outputs = prepare(
            args.role,
            args.story.strip(),
            args.pr.strip(),
            paused=os.environ.get("SW_AGENTS_PAUSED", "").strip().lower() == "true",
            ref=os.environ.get("GITHUB_REF", ""),
            github=github,
        )
    except RefusedError as error:
        print(f"::error::agent run refused: {error}")
        return 1
    lines = [f"{name}={value}" for name, value in outputs.items()]
    print("\n".join(lines))
    if path := os.environ.get("GITHUB_OUTPUT"):
        with open(path, "a", encoding="utf-8") as handle:
            handle.write("\n".join(lines) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
