"""Tests for the trading calendars (reference/calendars/) and their generator (docs/specs/SW-17.md).

The schema covers shape; the rules a JSON Schema cannot express are checked here.
"""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

from engine import calendars

ROOT = Path(__file__).resolve().parents[2]
CALENDAR_DIR = ROOT / "reference" / "calendars"
SCHEMA = ROOT / "config" / "schemas" / "trading_calendar.schema.json"
KNOWN = ROOT / "tests" / "fixtures" / "calendars" / "known_days.yaml"


class UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects a mapping with two equal keys instead of keeping the last."""

    def construct_mapping(self, node: yaml.MappingNode, deep: bool = False) -> dict[Any, Any]:
        seen: set[Any] = set()
        for key_node, _ in node.value:
            key = self.construct_object(key_node, deep=deep)
            if key in seen:
                raise yaml.constructor.ConstructorError(
                    None, None, f"duplicate key {key!r}", key_node.start_mark
                )
            seen.add(key)
        return super().construct_mapping(node, deep=deep)


def load(text: str) -> dict[str, Any]:
    data = yaml.load(text, Loader=UniqueKeyLoader)
    assert isinstance(data, dict)
    return data


def validate(name: str, text: str) -> None:
    """Raise if the file breaks the schema or a rule the schema cannot express."""
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    data = load(text)
    validator.validate(data)

    if name != calendars.file_name(data["calendar"], data["year"]):
        raise ValueError(f"{name}: file name does not match calendar and year")
    days = [date.fromisoformat(c["date"]) for c in data["closures"]]
    if any(d.year != data["year"] for d in days):
        raise ValueError(f"{name}: closure outside the year")
    if any(d.weekday() >= 5 for d in days):
        raise ValueError(f"{name}: closure on a weekend")
    if days != sorted(set(days)):
        raise ValueError(f"{name}: closures not strictly ascending")


def expected_names() -> set[str]:
    return {
        calendars.file_name(c, y)
        for c in calendars.CALENDARS
        for y in range(calendars.FIRST_YEAR, calendars.LAST_YEAR + 1)
    }


def test_files_cover_all_years() -> None:
    assert len(expected_names()) == 52
    assert {p.name for p in CALENDAR_DIR.glob("*.yaml")} == expected_names()


def test_real_calendars_are_valid() -> None:
    for path in sorted(CALENDAR_DIR.glob("*.yaml")):
        validate(path.name, path.read_text())


def test_files_are_up_to_date() -> None:
    assert calendars.main(["--check"]) == 0


def test_generator_is_deterministic(tmp_path: Path) -> None:
    first, second = tmp_path / "a", tmp_path / "b"
    args = ["--from-year", "2024", "--to-year", "2026"]
    assert calendars.main([*args, "--recorded-date", "2026-01-05", "--out-dir", str(first)]) == 0
    assert calendars.main([*args, "--recorded-date", "2026-01-05", "--out-dir", str(second)]) == 0
    before = {p.name: p.read_bytes() for p in first.glob("*.yaml")}
    assert len(before) == 6
    assert before == {p.name: p.read_bytes() for p in second.glob("*.yaml")}
    assert calendars.main([*args, "--recorded-date", "2027-02-02", "--out-dir", str(first)]) == 0
    assert before == {p.name: p.read_bytes() for p in first.glob("*.yaml")}


def test_known_days() -> None:
    known = yaml.safe_load(KNOWN.read_text())
    for calendar, days in known["closures"].items():
        for day in days:
            year = int(day[:4])
            assert date.fromisoformat(day) in {c.date for c in calendars.closures(calendar, year)}
    for calendar, days in known["sessions"].items():
        for day in days:
            year = int(day[:4])
            assert date.fromisoformat(day) not in {
                c.date for c in calendars.closures(calendar, year)
            }


def good(**fields: str) -> str:
    values = {
        "version": "1",
        "calendar": "XWAR",
        "year": "2025",
        "recorded_date": '"2026-11-17"',
        "closures": '\n  - date: "2025-01-01"\n    name: New Year\n  - date: "2025-12-31"\n'
        "    name: Eve",
    } | fields
    return "\n".join(f"{k}: {v}" for k, v in values.items()) + "\n"


def test_good_synthetic_calendar_is_valid() -> None:
    validate("xwar_2025.yaml", good())


BAD = {
    "unknown calendar": ("xwar_2025.yaml", good(calendar="LSE")),
    "unknown field": ("xwar_2025.yaml", good() + "extra: 1\n"),
    "bad date": ("xwar_2025.yaml", good(recorded_date='"2026-13-01"')),
    "closure on a Saturday": (
        "xwar_2025.yaml",
        good(closures='\n  - date: "2025-01-04"\n    name: Saturday'),
    ),
    "closure outside the year": (
        "xwar_2025.yaml",
        good(closures='\n  - date: "2024-12-31"\n    name: Eve'),
    ),
    "closures out of order": (
        "xwar_2025.yaml",
        good(
            closures='\n  - date: "2025-12-31"\n    name: Eve\n  - date: "2025-01-01"\n    name: A'
        ),
    ),
    "duplicate key": ("xwar_2025.yaml", good() + "year: 2025\n"),
    "file name not matching": ("nbp_2025.yaml", good()),
}


@pytest.mark.parametrize(("name", "text"), BAD.values(), ids=BAD.keys())
def test_bad_calendar_fails(name: str, text: str) -> None:
    with pytest.raises((yaml.YAMLError, ValidationError, ValueError)):
        validate(name, text)


def test_year_outside_the_calendar_range_raises() -> None:
    for calendar in calendars.CALENDARS:
        with pytest.raises(ValueError, match="outside"):
            calendars.closures(calendar, calendars.LAST_YEAR + 1)
