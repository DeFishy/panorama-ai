"""Проверки черновика контракта карточки contracts/card.schema.json на фиктивной карточке."""

import copy
import json
from collections.abc import Iterator
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((ROOT / "contracts" / "card.schema.json").read_text(encoding="utf-8"))
EXAMPLE = json.loads(
    (ROOT / "tests" / "fixtures" / "cards" / "example.json").read_text(encoding="utf-8")
)
VALIDATOR = Draft202012Validator(SCHEMA, format_checker=Draft202012Validator.FORMAT_CHECKER)


def walk(node: object) -> Iterator[dict]:
    """Все словари карточки, на любой глубине."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def reference_errors(card: dict) -> list[str]:
    """Ссылки, которые JSON Schema проверить не может: source_id и based_on внутри карточки."""
    errors = []
    source_ids = {source["source_id"] for source in card["sources"]}
    sections = (card["dossier"], card["changes"], card["risks"], card["scenarios"], card["watch"])
    nodes = [node for section in sections for node in walk(section)]

    ids = [node["id"] for node in nodes if "id" in node]
    duplicates = sorted({item for item in ids if ids.count(item) > 1})
    errors += [f"повторяется id {item}" for item in duplicates]

    for node in nodes:
        for ref in node.get("source_refs", []):
            if ref["source_id"] not in source_ids:
                errors.append(f"{node.get('id')}: нет источника {ref['source_id']}")
        for target in node.get("based_on", []):
            if target not in ids:
                errors.append(f"{node.get('id')}: based_on ведёт на несуществующий {target}")
    return errors


def schema_errors(card: dict) -> list[str]:
    return [error.message for error in VALIDATOR.iter_errors(card)]


def test_schema_itself_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_example_card_is_valid():
    assert schema_errors(EXAMPLE) == []
    assert reference_errors(EXAMPLE) == []


def drop_fact_source_refs(card):
    del card["changes"]["reasons"][0]["source_refs"]


def drop_interpretation_source_refs(card):
    del card["changes"]["reasons"][1]["source_refs"]


def drop_scenario_statement_basis(card):
    card["dossier"]["strategy"] = {
        "statements": [{"id": "d-strategy-1", "kind": "scenario", "text": "если X, то Y"}]
    }


def drop_negative_scenario(card):
    del card["scenarios"]["negative"]


def add_fourth_scenario(card):
    card["scenarios"]["optimistic"] = copy.deepcopy(card["scenarios"]["positive"])


def add_probability(card):
    card["scenarios"]["base"]["probability"] = 0.6


def drop_metric_source_refs(card):
    card["changes"]["metrics"][0]["source_refs"] = []


def null_metric_without_reason(card):
    del card["changes"]["metrics"][2]["no_data_reason"]


def turn_off_ai_label(card):
    card["limitations"]["ai_generated"] = False


def add_status_field(card):
    card["status"] = "published"


def watch_without_date(card):
    del card["watch"][0]["date_note"]


def bad_sha256(card):
    card["sources"][0]["sha256"] = "abc"


@pytest.mark.parametrize(
    "break_card",
    [
        drop_fact_source_refs,
        drop_interpretation_source_refs,
        drop_scenario_statement_basis,
        drop_negative_scenario,
        add_fourth_scenario,
        add_probability,
        drop_metric_source_refs,
        null_metric_without_reason,
        turn_off_ai_label,
        add_status_field,
        watch_without_date,
        bad_sha256,
    ],
)
def test_schema_rejects_broken_card(break_card):
    card = copy.deepcopy(EXAMPLE)
    break_card(card)

    assert schema_errors(card) != []


def test_reference_to_unknown_source_is_caught():
    card = copy.deepcopy(EXAMPLE)
    card["changes"]["reasons"][0]["source_refs"][0]["source_id"] = "s404"

    assert schema_errors(card) == []
    assert reference_errors(card) == ["r-1: нет источника s404"]


def test_based_on_unknown_id_is_caught():
    card = copy.deepcopy(EXAMPLE)
    card["scenarios"]["base"]["conditions"][0]["based_on"] = ["r-404"]

    assert reference_errors(card) == ["sc-base-1: based_on ведёт на несуществующий r-404"]


def test_duplicate_ids_are_caught():
    card = copy.deepcopy(EXAMPLE)
    card["changes"]["reasons"][1]["id"] = "r-1"

    assert "повторяется id r-1" in reference_errors(card)
