"""Tests for the instrument register (reference/instrument_register.yaml) and its schema.

The schema covers shape and patterns; the rules a JSON Schema cannot express are checked here
(docs/specs/SW-14.md). No engine code reads the register yet, so the loader lives here too.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError

ROOT = Path(__file__).resolve().parents[2]
REGISTER = ROOT / "reference" / "instrument_register.yaml"
SCHEMA = ROOT / "config" / "schemas" / "instrument_register.schema.json"


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


def load_register(text: str) -> dict[str, Any]:
    data = yaml.load(text, Loader=UniqueKeyLoader)
    assert isinstance(data, dict)
    return data


def validate(register: dict[str, Any]) -> None:
    """Raise if the register breaks the schema or a rule the schema cannot express."""
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)
    validator.validate(register)

    owner: dict[tuple[str, str], str] = {}
    for code, instrument in register["instruments"].items():
        for version in instrument["versions"]:
            if version["asset_class"] == "fx":
                if code[-3:] != version["quote_ccy"]:
                    raise ValueError(f"{code}: quote currency is not {version['quote_ccy']}")
                if version["current_symbol"] != code.removeprefix("FX."):
                    raise ValueError(f"{code}: current_symbol {version['current_symbol']}")
        for field in ("versions", "source_ids"):
            dates = [entry["valid_from_date"] for entry in instrument[field]]
            if dates != sorted(dates):
                raise ValueError(f"{code}: {field} not in ascending valid_from_date order")
        for source_id in instrument["source_ids"]:
            key = (source_id["source"], source_id["source_instrument_id"])
            if owner.setdefault(key, code) != code:
                raise ValueError(f"{key} maps to {owner[key]} and {code}")


def test_real_register_is_valid() -> None:
    validate(load_register(REGISTER.read_text()))


def test_register_lists_m1_instruments() -> None:
    instruments = load_register(REGISTER.read_text())["instruments"]
    expected = {"FX.EURPLN": "A/EUR", "FX.USDPLN": "A/USD", "FX.CHFPLN": "A/CHF"}
    assert set(instruments) == set(expected)
    required = {"valid_from_date", "recorded_date", "current_symbol", "asset_class", "quote_ccy"}
    for code, nbp_id in expected.items():
        assert any(required <= set(v) for v in instruments[code]["versions"])
        nbp = [s for s in instruments[code]["source_ids"] if s["source"] == "nbp"]
        assert [s["source_instrument_id"] for s in nbp] == [nbp_id]


def entry(code: str, nbp_id: str, **version: str) -> str:
    """One synthetic instrument as YAML, with version fields overridden or dropped."""
    fields = {
        "valid_from_date": '"2002-01-02"',
        "recorded_date": '"2026-01-05"',
        "current_symbol": code.removeprefix("FX."),
        "asset_class": "fx",
        "quote_ccy": "PLN",
    } | version
    lines = [f"{k}: {v}" for k, v in fields.items() if v]
    body = "\n        ".join(lines)
    return f"""  {code}:
    versions:
      - {body}
    source_ids:
      - source: nbp
        source_instrument_id: {nbp_id}
        valid_from_date: "2002-01-02"
        recorded_date: "2026-01-05"
"""


def register(*entries: str) -> str:
    return "version: 1\ninstruments:\n" + "".join(entries)


TWO_VERSIONS_OUT_OF_ORDER = """version: 1
instruments:
  FX.EURPLN:
    versions:
      - valid_from_date: "2010-01-04"
        recorded_date: "2026-01-05"
        current_symbol: EURPLN
        asset_class: fx
        quote_ccy: PLN
      - valid_from_date: "2002-01-02"
        recorded_date: "2026-01-05"
        current_symbol: EURPLN
        asset_class: fx
        quote_ccy: PLN
    source_ids:
      - source: nbp
        source_instrument_id: A/EUR
        valid_from_date: "2002-01-02"
        recorded_date: "2026-01-05"
"""

BAD_REGISTERS = {
    "duplicate code": register(entry("FX.EURPLN", "A/EUR"), entry("FX.EURPLN", "A/USD")),
    "code FX.EUR-PLN": register(entry("FX.EUR-PLN", "A/EUR", current_symbol="EUR-PLN")),
    "missing quote_ccy": register(entry("FX.EURPLN", "A/EUR", quote_ccy="")),
    "unknown field": register(entry("FX.EURPLN", "A/EUR", ticker="EURPLN")),
    "bad date": register(entry("FX.EURPLN", "A/EUR", valid_from_date='"2002-13-02"')),
    "quote currency not quote_ccy": register(entry("FX.EURPLN", "A/EUR", quote_ccy="EUR")),
    "one NBP identifier on two instruments": register(
        entry("FX.EURPLN", "A/EUR"), entry("FX.USDPLN", "A/EUR")
    ),
    "versions out of order": TWO_VERSIONS_OUT_OF_ORDER,
}


def test_good_synthetic_register_is_valid() -> None:
    validate(load_register(register(entry("FX.EURPLN", "A/EUR"), entry("FX.USDPLN", "A/USD"))))


@pytest.mark.parametrize("text", BAD_REGISTERS.values(), ids=BAD_REGISTERS.keys())
def test_bad_register_fails(text: str) -> None:
    with pytest.raises((yaml.YAMLError, ValidationError, ValueError)):
        validate(load_register(text))
