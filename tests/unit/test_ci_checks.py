"""Unit tests for the CI check scripts in .github/scripts/."""

import importlib.util
from pathlib import Path
from types import ModuleType

SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


change = load("check_change")
docs = load("check_docs")
no_real_data = load("check_no_real_data")

BODY = """- **Story:** https://rrogoz-sw.atlassian.net/browse/SW-12
- **Spec:** docs/specs/SW-12.md

## What
NBP connector.
## Why
M1 FX history.
## How it was tested
tests/contract/test_nbp.py
## Docs changed
config/sources/nbp.yaml
## Definition of Done
- [x] Acceptance criteria met
"""


def test_change_passes_a_good_pull_request() -> None:
    title = "feat(connectors): add NBP connector [SW-12]"
    assert change.check(title, "SW-12-nbp-connector", BODY) == []


def test_change_rejects_bad_title_branch_and_empty_section() -> None:
    body = BODY.replace("NBP connector.", "<!-- The change. -->")
    errors = change.check("Add NBP connector", "feature/nbp", body)
    assert any("title" in e for e in errors)
    assert any("branch" in e for e in errors)
    assert any("'## What' is empty" in e for e in errors)


def test_change_rejects_branch_key_that_differs_from_title() -> None:
    errors = change.check("fix: handle holiday [SW-12]", "SW-13-holiday", BODY)
    assert errors == ["branch key SW-13 differs from title key SW-12"]


def test_change_rejects_session_branches_after_m0() -> None:
    title = "feat(connectors): add NBP connector [SW-12]"
    errors = change.check(title, "claude/project-thread-abc123", BODY)
    assert any("branch" in e for e in errors)


def test_docs_slug_matches_github_anchors() -> None:
    assert docs.slug("Stage 2 requirements") == "stage-2-requirements"
    assert docs.slug("What standards must guarantee?") == "what-standards-must-guarantee"


def test_no_real_data_rejects_data_files_outside_fixtures() -> None:
    errors = no_real_data.check(["prices.parquet", "src/engine/rates.csv"])
    assert len(errors) == 2
    assert no_real_data.check(["README.md"]) == []
