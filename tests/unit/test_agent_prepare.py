"""Unit tests for the agent run check (pause switch, main only, spec, review rounds)."""

import importlib.util
from pathlib import Path
from types import ModuleType
from typing import Any

import pytest

SCRIPTS = Path(__file__).resolve().parents[2] / ".github" / "scripts"
MAIN = "refs/heads/main"


def load(name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / f"{name}.py")
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


agent = load("agent_prepare")


class FakeGitHub:
    repository = "rrogoz/stock-warehouse"

    def __init__(self, pull: dict[str, Any] | None, rejections: int = 0) -> None:
        self.pull = pull
        self.rejections = rejections

    def get(self, path: str) -> Any:
        return self.pull

    def changes_requested(self, number: int) -> int:
        return self.rejections


def pull(repo: str = "rrogoz/stock-warehouse", title: str = "feat: x [SW-12]") -> dict[str, Any]:
    return {
        "state": "open",
        "title": title,
        "head": {"ref": "SW-12-x", "sha": "abc", "repo": {"full_name": repo}},
    }


def refused(**kwargs: Any) -> str:
    args = {"role": "refine", "story": "SW-12", "pr": "", "paused": False, "ref": MAIN}
    args.update(kwargs)
    with pytest.raises(agent.RefusedError) as error:
        agent.prepare(args.pop("role"), args.pop("story"), args.pop("pr"), github=None, **args)
    return str(error.value)


def test_story_role_passes_with_a_key() -> None:
    out = agent.prepare("refine", "SW-12", "", paused=False, ref=MAIN, github=None)
    assert out["story"] == "SW-12"
    assert out["branch"] == ""


def test_pause_switch_main_only_and_bad_key_refuse() -> None:
    assert "paused" in refused(paused=True)
    assert "main only" in refused(ref="refs/heads/SW-12-x")
    assert "not a story key" in refused(story="SW-12; rm -rf /")


def test_implement_needs_a_spec_on_main(tmp_path: Path) -> None:
    with pytest.raises(agent.RefusedError, match="no approved spec"):
        agent.prepare("implement", "SW-12", "", paused=False, ref=MAIN, github=None, root=tmp_path)
    (tmp_path / "docs" / "specs").mkdir(parents=True)
    (tmp_path / "docs" / "specs" / "SW-12.md").write_text("# Spec\n")
    out = agent.prepare(
        "implement", "SW-12", "", paused=False, ref=MAIN, github=None, root=tmp_path
    )
    assert out["story"] == "SW-12"


def test_review_resolves_story_branch_and_round() -> None:
    out = agent.prepare("review", "", "42", paused=False, ref=MAIN, github=FakeGitHub(pull(), 1))
    assert out == {"story": "SW-12", "pr": "42", "branch": "SW-12-x", "sha": "abc", "round": "2"}


def test_pull_request_roles_refuse_forks_missing_keys_and_a_fourth_round() -> None:
    def run(github: FakeGitHub, pr: str = "42") -> str:
        with pytest.raises(agent.RefusedError) as error:
            agent.prepare("fix", "", pr, paused=False, ref=MAIN, github=github)
        return str(error.value)

    assert "not a pull request number" in run(FakeGitHub(pull()), pr="x")
    assert "not open" in run(FakeGitHub(None))
    assert "fork" in run(FakeGitHub(pull(repo="someone/fork")))
    assert "no story key" in run(FakeGitHub(pull(title="feat: x")))
    assert "rejected 3 times" in run(FakeGitHub(pull(), 3))
