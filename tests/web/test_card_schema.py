"""Проверки черновика контракта карточки contracts/card.schema.json на фиктивной карточке."""

import copy
import json

import pytest
from jsonschema import Draft202012Validator

from panorama_web.cards import (
    ROOT,
    SCHEMA_PATH,
    card_errors,
    format_errors,
    reference_errors,
    schema_errors,
)

SCHEMA = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
EXAMPLE = json.loads(
    (ROOT / "tests" / "fixtures" / "cards" / "example.json").read_text(encoding="utf-8")
)


def test_schema_itself_is_valid():
    Draft202012Validator.check_schema(SCHEMA)


def test_example_card_is_valid():
    assert schema_errors(EXAMPLE) == []
    assert reference_errors(EXAMPLE) == []
    assert format_errors(EXAMPLE) == []


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


@pytest.mark.parametrize("url", ["javascript:alert(1)", "ftp://example.com/a.pdf", "example.com"])
def test_source_url_must_be_http(url):
    # jsonschema без пакета rfc3987 формат uri не проверяет, поэтому проверка своя.
    card = copy.deepcopy(EXAMPLE)
    card["sources"][0]["url"] = url

    assert format_errors(card) == ["s1: ссылка не http(s)"]


@pytest.mark.parametrize(
    ("value", "error"),
    [
        ("вчера", "generated_at: не дата и время ISO 8601"),
        ("2026-10-31T12:00:00", "generated_at: нет часового пояса"),
    ],
)
def test_generated_at_must_be_datetime_with_timezone(value, error):
    card = copy.deepcopy(EXAMPLE)
    card["generated_at"] = value

    assert format_errors(card) == [error]


def test_card_errors_stops_after_schema_errors():
    card = copy.deepcopy(EXAMPLE)
    del card["sources"]

    errors = card_errors(card)

    assert errors != []
    assert all("нет источника" not in error for error in errors)


def test_card_errors_rejects_non_object():
    assert card_errors([]) == ["карточка не объект JSON"]
