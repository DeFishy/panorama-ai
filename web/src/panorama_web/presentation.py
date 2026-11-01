"""Подписи и форматирование для страниц: всё, что превращает поля карточки в текст по-русски.

Числа здесь только форматируются. Считает их конвейер (инвариант 1), сайт ничего не пересчитывает.
"""

from datetime import date, datetime

NBSP = " "
MINUS = "−"

KIND_LABELS = {"fact": "Факт", "interpretation": "Интерпретация", "scenario": "Сценарий"}
ATTRIBUTION_LABELS = {"company": "по заявлению компании", "media": "по сообщению СМИ"}

# Порядок блоков досье по шаблону из раздела 5 брифа (D-18).
DOSSIER_BLOCKS = {
    "passport": "Паспорт компании",
    "financials": "Финансовая динамика",
    "debt_liquidity": "Долг и ликвидность",
    "strategy": "Стратегия и проекты",
    "sensitivity": "Карта чувствительности",
    "context": "Внешний контекст",
    "unknowns": "Что неизвестно",
    "event_log": "Журнал событий",
}

RISK_CATEGORIES = {
    "debt": "Долговая нагрузка",
    "prices_rates": "Цены и ставки",
    "post_period": "События после отчётной даты",
    "auditor": "Замечания аудитора",
    "other": "Прочие риски",
}

SCENARIOS = {"base": "Базовый", "negative": "Негативный", "positive": "Позитивный"}

EVENT_TYPES = {
    "reporting": "Отчётность",
    "dividends": "Дивиденды",
    "meeting": "Собрание акционеров",
    "offer": "Оферта",
    "other": "Событие",
}

SOURCE_LEVELS = {
    1: "первичный документ",
    2: "позиция компании",
    3: "СМИ",
    4: "прочее",
}

STANDARDS = {"IFRS": "МСФО", "RAS": "РСБУ"}

MONTHS = (
    "января",
    "февраля",
    "марта",
    "апреля",
    "мая",
    "июня",
    "июля",
    "августа",
    "сентября",
    "октября",
    "ноября",
    "декабря",
)


def fmt_number(value: float | None) -> str:
    """12000 → «12 000», 2.1 → «2,1», None → «—». Не больше двух знаков после запятой."""
    if value is None:
        return "—"
    text = f"{abs(value):,.2f}".rstrip("0").rstrip(".")
    text = text.replace(",", NBSP).replace(".", ",")
    return f"{MINUS}{text}" if value < 0 and text != "0" else text


def fmt_pct(value: float | None) -> str:
    """Изменение в процентах со знаком: 9.09 → «+9,09 %», −3 → «−3 %»."""
    if value is None:
        return "—"
    text = fmt_number(value)
    sign = "+" if value > 0 and text != "0" else ""
    return f"{sign}{text}{NBSP}%"


def fmt_date(value: str) -> str:
    """«2026-10-28» → «28 октября 2026». Непонятную строку отдаём как есть."""
    try:
        day = date.fromisoformat(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{day.day}{NBSP}{MONTHS[day.month - 1]} {day.year}"


def fmt_datetime(value: str) -> str:
    """Дата и время в часовом поясе источника: «28 октября 2026, 18:30»."""
    try:
        moment = datetime.fromisoformat(value)
    except (TypeError, ValueError):
        return str(value)
    return f"{fmt_date(moment.date().isoformat())}, {moment:%H:%M}"


def fmt_locator(locator: dict) -> str:
    """Место в документе: «стр. 24 · Таблица 14. Сроки погашения займов»."""
    parts = []
    if "page" in locator:
        parts.append(f"стр.{NBSP}{locator['page']}")
    parts += [locator[key] for key in ("table", "section") if key in locator]
    return " · ".join(parts)


def shorten(text: str, limit: int = 80) -> str:
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",.;: ") + "…"


def card_view(card: dict) -> dict:
    """Справочники для шаблона страницы эмитента.

    source_numbers: номер источника в списке внизу страницы (для сносок «[1]»).
    targets: на что может ссылаться based_on сценария: подпись и якорь на странице.
    """
    source_numbers = {source["source_id"]: n for n, source in enumerate(card["sources"], 1)}

    targets = {}
    for metric in card["changes"]["metrics"]:
        targets[metric["id"]] = metric["name"]
    statements = [
        statement for block in card["dossier"].values() for statement in block.get("statements", [])
    ]
    statements += card["changes"]["reasons"]
    statements += [s for risk in card["risks"] for s in risk["statements"]]
    for statement in statements:
        targets[statement["id"]] = shorten(statement["text"])

    return {"source_numbers": source_numbers, "targets": targets}


FILTERS = {
    "number": fmt_number,
    "pct": fmt_pct,
    "date": fmt_date,
    "datetime": fmt_datetime,
    "locator": fmt_locator,
}

GLOBALS = {
    "KIND_LABELS": KIND_LABELS,
    "ATTRIBUTION_LABELS": ATTRIBUTION_LABELS,
    "DOSSIER_BLOCKS": DOSSIER_BLOCKS,
    "RISK_CATEGORIES": RISK_CATEGORIES,
    "SCENARIOS": SCENARIOS,
    "EVENT_TYPES": EVENT_TYPES,
    "SOURCE_LEVELS": SOURCE_LEVELS,
    "STANDARDS": STANDARDS,
}
