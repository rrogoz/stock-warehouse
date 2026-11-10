"""Smoke test: the package imports and the entry point runs."""

import pytest

from engine import __version__
from engine.__main__ import main


def test_version_is_set() -> None:
    assert __version__


def test_main_runs(capsys: pytest.CaptureFixture[str]) -> None:
    assert main() == 0
    assert "stock-warehouse engine" in capsys.readouterr().out
