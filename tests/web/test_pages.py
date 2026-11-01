"""Страницы сайта на фиктивной карточке «ПАО Пример»."""

import copy
import json
import re
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from panorama_web.app import create_app
from panorama_web.cards import ROOT, FileCardStore

FIXTURE = ROOT / "tests" / "fixtures" / "cards" / "example.json"
EXAMPLE = json.loads(FIXTURE.read_text(encoding="utf-8"))


def client_for(directory: Path) -> TestClient:
    return TestClient(create_app(FileCardStore(directory)))


def write_card(directory: Path, name: str, card: dict) -> None:
    (directory / name).write_text(json.dumps(card, ensure_ascii=False), encoding="utf-8")


@pytest.fixture
def cards_dir(tmp_path: Path) -> Path:
    shutil.copy(FIXTURE, tmp_path / "example.json")
    return tmp_path


@pytest.fixture
def client(cards_dir: Path) -> TestClient:
    return client_for(cards_dir)


def test_index_lists_issuer(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "ПАО Пример (вымышленная компания)" in response.text
    assert 'href="/issuers/prmr"' in response.text
    assert "3 кв. 2026" in response.text


def test_index_without_cards(tmp_path):
    response = client_for(tmp_path).get("/")

    assert response.status_code == 200
    assert "Карточек пока нет" in response.text


def test_issuer_page_has_all_blocks(client):
    html = client.get("/issuers/prmr").text

    for title in [
        "Досье",
        "Что изменилось",
        "Почему",
        "Риски",
        "Три сценария",
        "Что отслеживать",
        "Ограничения",
        "Источники",
    ]:
        assert f"<h2>{title}</h2>" in html
    for scenario in ["Базовый", "Негативный", "Позитивный"]:
        assert scenario in html


def test_issuer_page_labels_every_statement(client):
    html = client.get("/issuers/prmr").text

    assert 'class="label label--fact">Факт · по заявлению компании' in html
    assert 'class="label label--interpretation">Интерпретация' in html
    # Каждое утверждение карточки на странице, и у каждого есть метка.
    assert html.count('class="statement statement--') == html.count('class="label label--')


def test_issuer_page_shows_metrics_in_russian_format(client):
    html = client.get("/issuers/prmr").text

    assert "12 000" in html
    assert "+9,09 %" in html
    assert "Существенно" in html
    assert "Данных нет: Промежуточные дивиденды за период не объявлялись." in html


def test_issuer_page_links_refs_to_sources(client):
    html = client.get("/issuers/prmr").text

    assert 'id="source-s1"' in html
    assert '<a class="refs__num" href="#source-s1">[1]</a>' in html
    assert "стр. 24 · Таблица 14. Сроки погашения займов" in html
    assert 'href="#m-net-debt-ebitda">Чистый долг / EBITDA</a>' in html


def test_issuer_page_shows_no_data_block(client):
    html = client.get("/issuers/prmr").text

    assert "Компания не раскрывает структуру долга по валютам" in html


def test_issuer_page_has_disclaimer_and_ai_mark(client):
    html = client.get("/issuers/prmr").text

    assert EXAMPLE["limitations"]["disclaimer"] in html
    assert "Подготовлено с помощью ИИ" in html


def test_issuer_page_hides_generation_block(client):
    html = client.get("/issuers/prmr").text

    assert EXAMPLE["generation"]["model"] not in html
    assert EXAMPLE["generation"]["pipeline_version"] not in html


def test_unknown_issuer_is_404_page(client):
    response = client.get("/issuers/nope")

    assert response.status_code == 404
    assert "Страница не найдена" in response.text


def test_invalid_card_is_not_shown(cards_dir):
    card = copy.deepcopy(EXAMPLE)
    card["issuer"]["issuer_id"] = "broken"
    del card["changes"]["reasons"][0]["source_refs"]
    write_card(cards_dir, "broken.json", card)
    (cards_dir / "garbage.json").write_text("{не json", encoding="utf-8")
    client = client_for(cards_dir)

    assert client.get("/issuers/broken").status_code == 404
    assert "/issuers/broken" not in client.get("/").text
    assert client.get("/issuers/prmr").status_code == 200


def test_latest_card_version_wins(cards_dir):
    card = copy.deepcopy(EXAMPLE)
    card["card_version"] = 2
    card["changes"]["reasons"][1]["text"] = "Новая версия интерпретации."
    write_card(cards_dir, "example-v2.json", card)

    html = client_for(cards_dir).get("/issuers/prmr").text

    assert "Новая версия интерпретации." in html


def test_card_text_is_escaped(cards_dir):
    # Текст карточки это данные, а не разметка (инвариант 9).
    card = copy.deepcopy(EXAMPLE)
    card["card_version"] = 2
    card["changes"]["reasons"][0]["text"] = "<script>alert(1)</script>"
    write_card(cards_dir, "example-v2.json", card)

    html = client_for(cards_dir).get("/issuers/prmr").text

    assert "<script>alert(1)</script>" not in html
    assert "&lt;script&gt;" in html


def test_methodology_page(client):
    response = client.get("/methodology")

    assert response.status_code == 200
    assert "не индивидуальная инвестиционная рекомендация" in response.text


@pytest.mark.parametrize("path", ["/", "/issuers/prmr", "/methodology", "/issuers/nope"])
def test_pages_load_nothing_from_other_hosts(client, path):
    html = client.get(path).text

    assert "<script" not in html
    for tag in re.findall(r"<link[^>]*>", html):
        assert 'href="/static/' in tag


def test_stylesheet_is_served(client):
    response = client.get("/static/style.css")

    assert response.status_code == 200
    assert "text/css" in response.headers["content-type"]
