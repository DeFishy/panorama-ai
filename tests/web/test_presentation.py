"""Форматирование чисел и дат по-русски."""

import pytest

from panorama_web.presentation import fmt_date, fmt_datetime, fmt_locator, fmt_number, fmt_pct

NBSP = " "


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (12000, f"12{NBSP}000"),
        (12000.0, f"12{NBSP}000"),
        (1234567.891, f"1{NBSP}234{NBSP}567,89"),
        (2.1, "2,1"),
        (9.09, "9,09"),
        (0, "0"),
        (-0.001, "0"),
        (-1500.5, f"−1{NBSP}500,5"),
        (None, "—"),
    ],
)
def test_fmt_number(value, text):
    assert fmt_number(value) == text


@pytest.mark.parametrize(
    ("value", "text"),
    [
        (9.09, f"+9,09{NBSP}%"),
        (-3, f"−3{NBSP}%"),
        (0, f"0{NBSP}%"),
        (None, "—"),
    ],
)
def test_fmt_pct(value, text):
    assert fmt_pct(value) == text


def test_fmt_date():
    assert fmt_date("2026-10-28") == f"28{NBSP}октября 2026"
    assert fmt_date("не дата") == "не дата"


def test_fmt_datetime_keeps_source_timezone():
    assert fmt_datetime("2026-10-28T18:30:00+03:00") == f"28{NBSP}октября 2026, 18:30"


def test_fmt_locator():
    locator = {"page": 24, "table": "Таблица 14", "section": "Примечание 5"}

    assert fmt_locator(locator) == f"стр.{NBSP}24 · Таблица 14 · Примечание 5"
    assert fmt_locator({"section": "Примечание 18"}) == "Примечание 18"
