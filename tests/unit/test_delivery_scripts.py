"""Unit tests for the Jira script, the consistency check and the metrics report."""

import importlib.util
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jira = load("jira")
consistency = load("check_consistency")
metrics = load("report_metrics")


class FakeJira(jira.Jira):
    """Records calls and answers from a canned map of (method, path prefix)."""

    def __init__(self, answers: dict[tuple[str, str], Any] | None = None) -> None:
        super().__init__("https://example.atlassian.net", "agent@example.com", "token")
        self.answers = answers or {}
        self.calls: list[tuple[str, str, Any]] = []

    def call(self, method: str, path: str, body: Any = None) -> Any:
        self.calls.append((method, path, body))
        for (m, prefix), answer in self.answers.items():
            if m == method and path.startswith(prefix):
                return answer
        return None


def story(key: str, status: str, labels: list[str] | None = None) -> dict[str, Any]:
    return {"key": key, "fields": {"status": {"name": status}, "labels": labels or []}}


# Jira script


def test_roles_move_only_to_their_states() -> None:
    assert jira.allowed("refine", "Ready")
    assert jira.allowed("refine", "needs input")
    assert jira.allowed("ci", "Done")
    assert not jira.allowed("refine", "Done")
    assert not jira.allowed("implement", "Done")
    assert not jira.allowed("plan", "Ready")
    assert jira.allowed("review", "Needs input")
    assert not jira.allowed("review", "Ready")


def test_move_refused_for_role_never_calls_jira() -> None:
    fake = FakeJira()
    with pytest.raises(jira.JiraError, match="may not move"):
        fake.move("SW-12", "Done", "implement")
    assert fake.calls == []


def test_move_uses_the_transition_to_the_target_state() -> None:
    transitions = {"transitions": [{"id": "61", "to": {"name": "In Progress"}}]}
    transitions["transitions"].append({"id": "71", "to": {"name": "In review"}})
    fake = FakeJira({("GET", "/rest/api/2/issue/SW-12/transitions"): transitions})
    fake.move("SW-12", "In review", "implement")
    assert fake.calls[-1] == (
        "POST",
        "/rest/api/2/issue/SW-12/transitions",
        {"transition": {"id": "71"}},
    )


def test_comment_is_tagged_with_the_role() -> None:
    fake = FakeJira()
    fake.comment("SW-12", "refine", "Ready: all fields filled.")
    assert fake.calls[0][2] == {"body": "[refinement] Ready: all fields filled."}


def test_rejects_keys_outside_the_project() -> None:
    with pytest.raises(jira.JiraError, match="not a SW story key"):
        FakeJira().issue("ABC-1")


def test_push_creates_new_stories_and_refuses_stories_past_backlog() -> None:
    fake = FakeJira(
        {
            ("POST", "/rest/api/2/issue"): {"key": "SW-20"},
            ("GET", "/rest/api/2/issue/SW-12"): {"fields": {"status": {"name": "Ready"}}},
        }
    )
    assert fake.push([{"summary": "Add NBP connector", "epic": "SW-1"}]) == ["SW-20"]
    created = fake.calls[0][2]["fields"]
    assert created["project"] == {"key": "SW"}
    assert created["parent"] == {"key": "SW-1"}
    with pytest.raises(jira.JiraError, match="only Backlog"):
        fake.push([{"key": "SW-12", "summary": "Changed"}])


# Consistency check


@pytest.mark.parametrize(
    ("today", "expected"),
    [
        (date(2026, 11, 10), date(2026, 11, 9)),  # Tuesday -> Monday
        (date(2026, 11, 9), date(2026, 11, 6)),  # Monday -> Friday
        (date(2026, 11, 8), date(2026, 11, 6)),  # Sunday -> Friday
    ],
)
def test_last_weekday(today: date, expected: date) -> None:
    assert consistency.last_weekday(today) == expected


def test_story_rules() -> None:
    pull = {"number": 7, "merged_at": "2026-11-05T10:00:00Z"}
    stories = [
        story("SW-12", "In Progress"),
        story("SW-13", "In Progress"),
        story("SW-14", "Done"),
        story("SW-15", "Done"),
        story("SW-3", "Done", ["bootstrap"]),
    ]
    released = datetime(2026, 11, 4, tzinfo=UTC)
    problems = consistency.story_problems(stories, {"SW-13"}, {"SW-14": pull}, released)
    assert problems == [
        "SW-12 is In progress but docs/specs/SW-12.md is not on main",
        "SW-14 is Done but #7 is not released to PROD yet",
        "SW-15 is Done but no merged pull request has [SW-15] in its title",
    ]
    later = datetime(2026, 11, 6, tzinfo=UTC)
    assert consistency.story_problems([stories[2]], set(), {"SW-14": pull}, later) == []


def test_prod_run_rules() -> None:
    today = date(2026, 11, 10)
    ok = {"created_at": "2026-11-09T18:00:00Z", "conclusion": "success", "html_url": "u"}
    failed = {"created_at": "2026-11-09T18:00:00Z", "conclusion": "failure", "html_url": "u"}
    older = {"created_at": "2026-11-06T18:00:00Z", "conclusion": "success", "html_url": "u"}
    assert consistency.prod_run_problem(None, today) is None
    assert consistency.prod_run_problem([ok], today) is None
    assert "did not succeed" in consistency.prod_run_problem([failed], today)
    assert "did not start" in consistency.prod_run_problem([older], today)


# Metrics report


def test_ready_at_takes_the_first_move_to_ready() -> None:
    changelog = [
        {
            "created": "2026-11-01T09:00:00.000+0100",
            "items": [{"field": "status", "toString": "Refinement"}],
        },
        {
            "created": "2026-11-02T09:00:00.000+0100",
            "items": [{"field": "status", "toString": "Ready"}],
        },
        {
            "created": "2026-11-03T09:00:00.000+0100",
            "items": [{"field": "status", "toString": "Ready"}],
        },
    ]
    assert metrics.ready_at(changelog) == datetime(2026, 11, 2, 8, tzinfo=UTC)
    assert metrics.ready_at([]) is None


def test_report_rows_and_empty_week() -> None:
    pull = {"number": 7, "merged_at": "2026-11-05T08:00:00Z", "html_url": "https://x/7"}
    line = metrics.row("SW-12", pull, 1, datetime(2026, 11, 2, 8, tzinfo=UTC))
    assert (
        line == "| SW-12 | [#7](https://x/7) | 1 | 3.0 days | not measured yet | not measured yet |"
    )
    since = datetime(2026, 11, 3, tzinfo=UTC)
    assert "No stories merged" in metrics.report([], since)
    assert metrics.HEADER in metrics.report([line], since)
