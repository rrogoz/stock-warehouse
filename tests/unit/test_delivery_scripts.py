"""Unit tests for the Jira script, the consistency check and the metrics report."""

import importlib.util
import json
from datetime import UTC, date, datetime
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest
import yaml

SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


jira = load("jira")
story_status = load("story_status")
agent_report = load("agent_report")
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


def test_jira_move_allowed() -> None:
    # SW-15: CI, not the implement agent, moves a change pull request's story.
    assert not jira.allowed("implement", "In review")
    assert jira.allowed("ci", "In review")
    assert jira.allowed("ci", "Awaiting release")


def test_move_refused_for_role_never_calls_jira() -> None:
    fake = FakeJira()
    with pytest.raises(jira.JiraError, match="may not move"):
        fake.move("SW-12", "Done", "implement")
    assert fake.calls == []


def test_move_uses_the_transition_to_the_target_state() -> None:
    transitions = {"transitions": [{"id": "61", "to": {"name": "In Progress"}}]}
    transitions["transitions"].append({"id": "71", "to": {"name": "In review"}})
    fake = FakeJira({("GET", "/rest/api/2/issue/SW-12/transitions"): transitions})
    fake.move("SW-12", "In review", "ci")
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


def test_verdict_sets_dropdown_option_and_reason() -> None:
    fake = FakeJira(
        {
            ("GET", "/rest/api/2/field"): [
                {"id": "customfield_1", "name": "Refinement verdict"},
                {"id": "customfield_2", "name": "Verdict reason"},
            ],
            ("GET", "/rest/api/2/issue/SW-12/editmeta"): {
                "fields": {"customfield_1": {"allowedValues": [{"value": "Ready"}]}}
            },
        }
    )
    fake.verdict("SW-12", "ready", " All fields present. ")
    put = [c for c in fake.calls if c[0] == "PUT"][0]
    assert put[2] == {
        "fields": {"customfield_1": {"value": "Ready"}, "customfield_2": "All fields present."}
    }


def test_verdict_refuses_unknown_option() -> None:
    with pytest.raises(jira.JiraError, match="no option 'split'"):
        jira.option_for("split", ["Ready", "Questions"])


# Story status (SW-15)


@pytest.mark.parametrize(
    ("action", "merged", "title", "expected"),
    [
        ("opened", False, "feat(reference): add register [SW-14]", ("SW-14", "In review")),
        ("reopened", False, "fix(ci): x [SW-15]", ("SW-15", "In review")),
        ("closed", True, "feat(reference): add register [SW-14]", ("SW-14", "Awaiting release")),
        ("closed", False, "feat(reference): add register [SW-14]", None),
        ("opened", False, "docs(specs): add spec [SW-15]", None),
        ("closed", True, "docs(specs): add spec [SW-15]", None),
        ("opened", False, "chore: no story key", None),
        ("synchronize", False, "fix(ci): x [SW-15]", None),
    ],
)
def test_story_status_target(
    action: str, merged: bool, title: str, expected: tuple[str, str] | None
) -> None:
    assert story_status.target(action, merged, title) == expected


def test_story_status_skips_current_state() -> None:
    fake = FakeJira({("GET", "/rest/api/2/issue/SW-14?"): story("SW-14", "In review")})
    assert "already" in story_status.apply(fake, "SW-14", "In review")
    assert all(method == "GET" for method, _, _ in fake.calls)


def test_story_status_moves() -> None:
    transitions = {"transitions": [{"id": "81", "to": {"name": "Awaiting release"}}]}
    fake = FakeJira(
        {
            ("GET", "/rest/api/2/issue/SW-14?"): story("SW-14", "In review"),
            ("GET", "/rest/api/2/issue/SW-14/transitions"): transitions,
        }
    )
    story_status.apply(fake, "SW-14", "Awaiting release")
    posts = [call for call in fake.calls if call[0] == "POST"]
    assert posts == [("POST", "/rest/api/2/issue/SW-14/transitions", {"transition": {"id": "81"}})]


# Agent report (SW-15)


def execution(denials: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    result: dict[str, Any] = {"type": "result", "subtype": "success"}
    if denials is not None:
        result["permission_denials"] = denials
    return [{"type": "system", "subtype": "init"}, result]


def test_agent_report(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    long_command = "gh pr edit 12 --body " + "x" * 500
    denied = [
        {"tool_name": "Bash", "tool_input": {"command": long_command}},
        {"tool_name": "Write", "tool_input": {"file_path": "/etc/passwd"}},
    ]
    text = agent_report.report(agent_report.denials(execution(denied)))
    rows = [line for line in text.splitlines() if line.startswith("| Bash") or "Write" in line]
    assert len(rows) == 2
    assert all(len(row) < agent_report.MAX_INPUT + 40 for row in rows)
    assert "No refused tool calls" in agent_report.report(agent_report.denials(execution(None)))

    summary = tmp_path / "summary.md"
    file = tmp_path / "execution.json"
    file.write_text(json.dumps(execution(denied)))
    with pytest.MonkeyPatch.context() as patch:
        patch.setenv("GITHUB_STEP_SUMMARY", str(summary))
        assert agent_report.main(["agent_report.py", str(file)]) == 0
    assert "| Write |" in summary.read_text()
    assert agent_report.main(["agent_report.py", str(tmp_path / "missing.json")]) == 0
    assert "notice" in capsys.readouterr().out


# Workflow settings (SW-15)

WORKFLOWS = SCRIPTS.parent / "workflows"
RUNBOOK = SCRIPTS.parents[1] / "docs" / "runbooks" / "run-an-agent.md"


def test_implement_task_leaves_move_to_ci() -> None:
    workflow = yaml.safe_load((WORKFLOWS / "agent-implement.yml").read_text())
    task = workflow["jobs"]["implement"]["with"]["task"]
    assert "move the story" not in task
    assert "CI moves the story" in task


def test_refine_default_model() -> None:
    workflow = yaml.safe_load((WORKFLOWS / "agent-refine.yml").read_text())
    # PyYAML reads the key "on" as True.
    model = workflow[True]["workflow_dispatch"]["inputs"]["model"]
    assert model["default"] == "sonnet"
    row = next(line for line in RUNBOOK.read_text().splitlines() if "`agent-refine`" in line)
    assert "sonnet" in row
    assert "haiku" not in row
