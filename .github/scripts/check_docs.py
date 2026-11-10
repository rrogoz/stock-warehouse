"""Docs check: links resolve, template sections are present, ADR statuses are valid.

Enforces the CI part of docs/standards/documentation.md. The required sections
of each document type are the level-2 headings of its template in docs/templates/.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LINK = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)\)")
FENCE = re.compile(r"^```.*?^```", re.DOTALL | re.MULTILINE)
CODE = re.compile(r"`[^`\n]*`")
STATUS = re.compile(r"^- \*\*Status:\*\* (Proposed|Accepted|Superseded by ADR-\d{3})$", re.M)
# Document type: (folder, file name pattern, template).
TYPES = (
    ("docs/adr", re.compile(r"^\d{4}-[a-z0-9-]+\.md$"), "adr.md"),
    ("docs/standards", re.compile(r"^(?!README)[a-z0-9-]+\.md$"), "standard.md"),
    ("docs/specs", re.compile(r"^SW-\d+\.md$"), "spec.md"),
    ("docs/runbooks", re.compile(r"^[a-z0-9-]+\.md$"), "runbook.md"),
)


def markdown_files() -> list[Path]:
    out = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    return [ROOT / line for line in out.splitlines() if (ROOT / line).is_file()]


def prose(text: str) -> str:
    """Text without code blocks or inline code, where links are not links."""
    return CODE.sub("", FENCE.sub("", text))


def slug(heading: str) -> str:
    """GitHub's anchor for a heading."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", heading).strip().lower()
    text = re.sub(r"[^\w\- ]", "", text)
    return text.replace(" ", "-")


def anchors(path: Path) -> set[str]:
    headings = re.findall(r"^#{1,6} (.+)$", prose(path.read_text(encoding="utf-8")), re.M)
    return {slug(h) for h in headings}


def headings(path: Path, level: int = 2) -> list[str]:
    marks = "#" * level
    return re.findall(rf"^{marks} (.+)$", prose(path.read_text(encoding="utf-8")), re.M)


def check_links(path: Path) -> list[str]:
    errors = []
    for target in LINK.findall(prose(path.read_text(encoding="utf-8"))):
        if re.match(r"^[a-z]+:", target):
            continue  # http, https, mailto: not checked offline
        file_part, _, anchor = target.partition("#")
        dest = (path.parent / file_part).resolve() if file_part else path
        name = path.relative_to(ROOT)
        if not dest.exists():
            errors.append(f"{name}: link {target} does not resolve")
        elif anchor and dest.suffix == ".md" and anchor not in anchors(dest):
            errors.append(f"{name}: link {target} has no heading #{anchor}")
    return errors


def check_sections(path: Path) -> list[str]:
    rel = path.relative_to(ROOT)
    for folder, pattern, template in TYPES:
        if str(rel.parent) == folder and pattern.match(rel.name):
            required = headings(ROOT / "docs/templates" / template)
            present = headings(path)
            return [f"{rel}: missing section '## {h}'" for h in required if h not in present]
    return []


def check_adrs() -> list[str]:
    errors = []
    index = (ROOT / "docs/adr/README.md").read_text(encoding="utf-8")
    for path in sorted((ROOT / "docs/adr").glob("[0-9][0-9][0-9][0-9]-*.md")):
        rel = path.relative_to(ROOT)
        text = path.read_text(encoding="utf-8")
        number = f"ADR-{path.name[1:4]}"
        if not text.startswith(f"# {number}: "):
            errors.append(f"{rel}: first line must be '# {number}: title'")
        status = STATUS.search(text)
        if not status:
            errors.append(f"{rel}: status must be Proposed, Accepted or Superseded by ADR-NNN")
            continue
        row = re.search(
            rf"^\| \[{number}\]\({re.escape(path.name)}\) \|.*\| (.+?) \|$", index, re.M
        )
        if not row:
            errors.append(f"{rel}: no row in docs/adr/README.md")
        elif row.group(1) != status.group(1):
            errors.append(f"{rel}: index says {row.group(1)!r}, file says {status.group(1)!r}")
    return errors


def main() -> int:
    errors: list[str] = []
    for path in markdown_files():
        errors += check_links(path) + check_sections(path)
    errors += check_adrs()
    for error in errors:
        print(f"docs check: {error}")
    if not errors:
        print("docs check: ok")
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
