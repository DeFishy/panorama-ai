"""Карточки эмитентов: проверка по контракту и хранилище для страниц сайта.

Пока карточки лежат JSON-файлами в папке (FileCardStore). Когда появится база (PR 4), рядом
встанет хранилище на PostgreSQL с тем же интерфейсом CardStore, а страницы не изменятся.
"""

import json
import logging
from collections.abc import Iterator
from datetime import datetime
from functools import cache
from pathlib import Path
from typing import Protocol
from urllib.parse import urlsplit

from jsonschema import Draft202012Validator

ROOT = Path(__file__).resolve().parents[3]
SCHEMA_PATH = ROOT / "contracts" / "card.schema.json"

log = logging.getLogger(__name__)


@cache
def validator() -> Draft202012Validator:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema, format_checker=Draft202012Validator.FORMAT_CHECKER)


def walk(node: object) -> Iterator[dict]:
    """Все словари карточки, на любой глубине."""
    if isinstance(node, dict):
        yield node
        for value in node.values():
            yield from walk(value)
    elif isinstance(node, list):
        for value in node:
            yield from walk(value)


def schema_errors(card: dict) -> list[str]:
    return [error.message for error in validator().iter_errors(card)]


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


def format_errors(card: dict) -> list[str]:
    """Форматы, которые jsonschema без дополнительных пакетов не проверяет: uri и date-time.

    Ссылку на источник сайт показывает как href, поэтому допускаем только http и https.
    """
    errors = []
    stamps = [("generated_at", card["generated_at"])]
    stamps += [(f"{s['source_id']}.retrieved_at", s["retrieved_at"]) for s in card["sources"]]
    for name, value in stamps:
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            errors.append(f"{name}: не дата и время ISO 8601")
            continue
        if parsed.tzinfo is None:
            errors.append(f"{name}: нет часового пояса")

    for source in card["sources"]:
        url = urlsplit(source["url"])
        if url.scheme not in ("http", "https") or not url.netloc:
            errors.append(f"{source['source_id']}: ссылка не http(s)")
    return errors


def card_errors(card: object) -> list[str]:
    """Все ошибки карточки. Пустой список: карточку можно показывать."""
    if not isinstance(card, dict):
        return ["карточка не объект JSON"]
    errors = schema_errors(card)
    if errors:
        # Остальные проверки рассчитывают на структуру из схемы.
        return errors
    return reference_errors(card) + format_errors(card)


class CardStore(Protocol):
    """Откуда сайт берёт карточки. Отдаёт только карточки, прошедшие проверку."""

    def list_cards(self) -> list[dict]:
        """Последняя карточка каждого эмитента, по алфавиту названий."""
        ...

    def get_card(self, issuer_id: str) -> dict | None:
        """Последняя карточка эмитента или None, если её нет."""
        ...


class FileCardStore:
    """Карточки из файлов *.json в папке. Временная замена базы до PR 4.

    Статус карточки (draft, published и т. п.) по контракту хранится в базе, а у файлов его
    нет: здесь любая карточка, прошедшая проверку, считается опубликованной. Папку читаем
    при каждом запросе: файлов единицы, зато новая карточка видна без перезапуска.
    """

    def __init__(self, directory: Path) -> None:
        self.directory = directory

    def _latest(self) -> dict[str, dict]:
        latest: dict[str, dict] = {}
        for path in sorted(self.directory.glob("*.json")):
            try:
                card = json.loads(path.read_text(encoding="utf-8"))
            except (OSError, ValueError) as error:
                log.warning("Карточка %s не прочитана: %s", path.name, error)
                continue
            errors = card_errors(card)
            if errors:
                log.warning("Карточка %s не прошла проверку: %s", path.name, "; ".join(errors))
                continue
            issuer_id = card["issuer"]["issuer_id"]
            current = latest.get(issuer_id)
            if current is None or _freshness(card) > _freshness(current):
                latest[issuer_id] = card
        return latest

    def list_cards(self) -> list[dict]:
        return sorted(self._latest().values(), key=lambda card: card["issuer"]["name"])

    def get_card(self, issuer_id: str) -> dict | None:
        return self._latest().get(issuer_id)


def _freshness(card: dict) -> tuple[str, int]:
    """Какая карточка новее: сначала по концу периода, затем по номеру версии."""
    return card["period"]["end_date"], card["card_version"]
