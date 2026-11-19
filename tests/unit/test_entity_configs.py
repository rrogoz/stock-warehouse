"""Tests for the entity configs (config/entities/*.yaml) and their schema (docs/specs/SW-19.md).

The schema covers shape; the rules a JSON Schema cannot express are checked here.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest
import yaml
from jsonschema import Draft202012Validator, ValidationError
from test_instrument_register import UniqueKeyLoader

from engine import dbt_models

ROOT = Path(__file__).resolve().parents[2]
ENTITIES = ROOT / "config" / "entities"
SCHEMA = ROOT / "config" / "schemas" / "entity.schema.json"


def load(text: str) -> dict[str, Any]:
    data = yaml.load(text, Loader=UniqueKeyLoader)
    assert isinstance(data, dict)
    return data


def validate(entities: dict[str, dict[str, Any]]) -> None:
    """Raise if a config, keyed by file stem, breaks the schema or a cross-field rule."""
    schema = json.loads(SCHEMA.read_text())
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    fields = {}
    for stem, entity in entities.items():
        validator.validate(entity)
        if entity["entity"] != stem:
            raise ValueError(f"{stem}.yaml names entity {entity['entity']}")
        names = [f["name"] for f in entity["fields"]]
        if len(names) != len(set(names)):
            raise ValueError(f"{stem}: duplicate field name")
        fields[stem] = {f["name"]: f for f in entity["fields"]}
    for stem, entity in entities.items():
        for name in dbt_models.key_fields(entity):
            if name not in fields[stem]:
                raise ValueError(f"{stem}: key field {name} is not a field")
            if not fields[stem][name]["required"]:
                raise ValueError(f"{stem}: key field {name} is not required")
        if entity["built_by"] == "dbt":
            missing = set(dbt_models.STANDARD) - set(fields[stem])
            if missing:
                raise ValueError(f"{stem}: missing standard fields {sorted(missing)}")
        for field in entity["fields"]:
            if "references" in field:
                target, column = field["references"].split(".")
                if column not in fields.get(target, {}):
                    raise ValueError(f"{stem}.{field['name']}: no {field['references']}")


def real_configs() -> dict[str, dict[str, Any]]:
    return {p.stem: load(p.read_text()) for p in sorted(ENTITIES.glob("*.yaml"))}


def test_entity_configs_are_valid() -> None:
    entities = real_configs()
    assert {"ops_run_log", "dim_instrument", "map_instrument_source"} <= set(entities)
    validate(entities)


def test_generated_models_up_to_date() -> None:
    assert dbt_models.main(["--check"]) == 0


def test_value_fields() -> None:
    entities = real_configs()
    assert dbt_models.key_fields(entities["dim_instrument"]) == [
        "instrument_code",
        "valid_from_date",
    ]
    assert dbt_models.value_fields(entities["dim_instrument"]) == [
        "current_symbol",
        "asset_class",
        "exchange",
        "quote_ccy",
    ]
    assert dbt_models.value_fields(entities["map_instrument_source"]) == ["source_instrument_id"]


GOOD = """version: 1
entity: dim_thing
layer: silver
description: A synthetic entity.
grain: one version of a thing
built_by: dbt
input: stg_reference__things
business_key: [thing_code]
scd2: true
fields:
  - {name: thing_code, type: varchar, required: true, description: Key.}
  - {name: valid_from_date, type: date, required: true, description: From.}
  - {name: owner_code, type: varchar, required: true, description: Owner.}
  - {name: known_at, type: timestamptz, required: true, description: Known.}
  - {name: run_id, type: varchar, required: true, description: Run.}
  - {name: record_hash, type: varchar, required: true, description: Hash.}
"""


def case(old: str, new: str, stem: str = "dim_thing") -> tuple[str, str]:
    assert old in GOOD
    return stem, GOOD.replace(old, new)


BAD = {
    "unknown key": case("scd2: true\n", "scd2: true\nowner: rafal\n"),
    "missing description": case("description: Owner.", "descr: Owner."),
    "bad prefix": case("entity: dim_thing", "entity: thing", stem="thing"),
    "name not matching file": case("entity: dim_thing", "entity: dim_other"),
    "unknown type": case("type: date", "type: datetime"),
    "duplicate YAML key": case("layer: silver\n", "layer: silver\nlayer: gold\n"),
    "key not a field": case("business_key: [thing_code]", "business_key: [thing_id]"),
    "SCD2 without valid_from_date": case(
        "  - {name: valid_from_date, type: date, required: true, description: From.}\n", ""
    ),
    "dbt entity without input": case("input: stg_reference__things\n", ""),
    "dbt entity without record_hash": case(
        "  - {name: record_hash, type: varchar, required: true, description: Hash.}\n", ""
    ),
    "reference to a missing entity": case(
        "description: Owner.}", "description: Owner., references: dim_owner.owner_code}"
    ),
}


def test_good_entity_config_is_valid() -> None:
    validate({"dim_thing": load(GOOD)})


@pytest.mark.parametrize(("stem", "text"), BAD.values(), ids=BAD.keys())
def test_bad_entity_config_fails(stem: str, text: str) -> None:
    with pytest.raises((yaml.YAMLError, ValidationError, ValueError)):
        validate({stem: load(text)})
