"""Change check: the pull request follows the change conventions standard.

Reads PR_TITLE, PR_BRANCH and PR_BODY from the environment and fails when the
title, branch or description breaks docs/standards/change-conventions.md.
"""

from __future__ import annotations

import os
import re
import sys

TYPES = ("feat", "fix", "docs", "test", "refactor", "chore", "ci")
TITLE = re.compile(rf"^(?:{'|'.join(TYPES)})(?:\([a-z0-9-]+\))?: \S.* \[(SW-\d+)\]$")
BRANCH = re.compile(r"^(SW-\d+)-[a-z0-9-]+$")
# M0 only: build sessions push to claude/project-thread-* branches. Removed in SW-9.
BOOTSTRAP_BRANCH = re.compile(r"^claude/project-thread-[a-z0-9]+$")
SECTIONS = ("What", "Why", "How it was tested", "Docs changed", "Definition of Done")
COMMENT = re.compile(r"<!--.*?-->", re.DOTALL)


def sections(body: str) -> dict[str, str]:
    """Split a Markdown body into its level-2 sections, comments removed."""
    found: dict[str, str] = {}
    current: str | None = None
    for line in COMMENT.sub("", body).splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            found[current] = ""
        elif current is not None:
            found[current] += line + "\n"
    return found


def check(title: str, branch: str, body: str) -> list[str]:
    errors: list[str] = []
    title_match = TITLE.match(title)
    key = title_match.group(1) if title_match else None
    if not title_match:
        errors.append(
            f"title {title!r} is not 'type(scope): summary [SW-NNN]' "
            f"with type one of {', '.join(TYPES)}"
        )
    branch_match = BRANCH.match(branch)
    if branch_match:
        if key and branch_match.group(1) != key:
            errors.append(f"branch key {branch_match.group(1)} differs from title key {key}")
    elif not BOOTSTRAP_BRANCH.match(branch):
        errors.append(f"branch {branch!r} is not '<story key>-short-title', e.g. SW-12-nbp")
    if key and f"browse/{key}" not in body:
        errors.append(f"description does not link the story {key}")
    if not re.search(r"\*\*Spec:\*\*\s*\S", COMMENT.sub("", body)):
        errors.append("description has no '**Spec:**' line (link the spec, or say none)")
    found = sections(body)
    for name in SECTIONS:
        if name not in found:
            errors.append(f"description is missing the section '## {name}'")
        elif not found[name].strip():
            errors.append(f"section '## {name}' is empty")
    return errors


def main() -> int:
    errors = check(
        os.environ.get("PR_TITLE", ""),
        os.environ.get("PR_BRANCH", ""),
        os.environ.get("PR_BODY", ""),
    )
    for error in errors:
        print(f"change check: {error}")
    if not errors:
        print("change check: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
