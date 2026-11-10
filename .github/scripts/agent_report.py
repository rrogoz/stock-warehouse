"""Agent report: list the tool calls an agent run was refused (ADR-011).

Reads the claude-code-action execution file and writes the final result's
permission denials to the run log and the job summary. Never fails the job:
a missing or unreadable file gives a notice and exit 0.

    python3 .github/scripts/agent_report.py "$EXECUTION_FILE"
"""

from __future__ import annotations

import json
import os
import sys
from typing import Any

MAX_INPUT = 300


def denials(messages: Any) -> list[dict[str, Any]]:
    """The permission denials of the last result message."""
    if not isinstance(messages, list):
        return []
    results = [m for m in messages if isinstance(m, dict) and m.get("type") == "result"]
    if not results:
        return []
    found = results[-1].get("permission_denials") or []
    return [d for d in found if isinstance(d, dict)]


def cell(text: str) -> str:
    text = " ".join(text.split()).replace("|", "\\|")
    return text if len(text) <= MAX_INPUT else text[: MAX_INPUT - 1] + "…"


def report(found: list[dict[str, Any]]) -> str:
    if not found:
        return "### Refused tool calls\n\nNo refused tool calls.\n"
    lines = ["### Refused tool calls", "", "| Tool | Input |", "| --- | --- |"]
    for denial in found:
        tool = cell(str(denial.get("tool_name", "?")))
        raw = denial.get("tool_input", "")
        text = raw if isinstance(raw, str) else json.dumps(raw, ensure_ascii=False)
        lines.append(f"| {tool} | {cell(text)} |")
    return "\n".join(lines) + "\n"


def main(argv: list[str]) -> int:
    path = argv[1] if len(argv) > 1 else ""
    try:
        with open(path, encoding="utf-8") as handle:
            messages = json.load(handle)
    except (OSError, ValueError) as error:
        print(f"::notice::no agent execution file to report on ({error})")
        return 0
    text = report(denials(messages))
    print(text)
    if summary := os.environ.get("GITHUB_STEP_SUMMARY"):
        with open(summary, "a", encoding="utf-8") as handle:
            handle.write(text)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
