"""Точка входа FastAPI."""

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.exceptions import HTTPException as StarletteHTTPException

from panorama_web.cards import ROOT, CardStore, FileCardStore
from panorama_web.presentation import FILTERS, GLOBALS, card_view

PACKAGE = Path(__file__).resolve().parent

templates = Jinja2Templates(directory=PACKAGE / "templates")
templates.env.filters.update(FILTERS)
templates.env.globals.update(GLOBALS)


def cards_dir() -> Path:
    """Папка с карточками. По умолчанию фиктивная карточка из тестов, для локальной разработки."""
    return Path(os.environ.get("PANORAMA_CARDS_DIR", ROOT / "tests" / "fixtures" / "cards"))


def create_app(store: CardStore) -> FastAPI:
    # Сайт закрыт приглашениями, поэтому автодокументацию API наружу не отдаём.
    app = FastAPI(title="Panorama AI", docs_url=None, redoc_url=None, openapi_url=None)
    app.mount("/static", StaticFiles(directory=PACKAGE / "static"), name="static")

    @app.exception_handler(StarletteHTTPException)
    async def not_found_page(request: Request, exc: StarletteHTTPException) -> Response:
        if exc.status_code == 404:
            return templates.TemplateResponse(request, "404.html", status_code=404)
        return await http_exception_handler(request, exc)

    @app.get("/health")
    def health() -> dict[str, str]:
        """Проверка живости процесса для мониторинга. Базу данных не опрашивает."""
        return {"status": "ok"}

    @app.get("/", response_class=HTMLResponse)
    def issuers(request: Request) -> Response:
        return templates.TemplateResponse(request, "index.html", {"cards": store.list_cards()})

    @app.get("/issuers/{issuer_id}", response_class=HTMLResponse)
    def issuer(request: Request, issuer_id: str) -> Response:
        card = store.get_card(issuer_id)
        if card is None:
            raise HTTPException(status_code=404)
        context = {"card": card, **card_view(card)}
        return templates.TemplateResponse(request, "issuer.html", context)

    @app.get("/methodology", response_class=HTMLResponse)
    def methodology(request: Request) -> Response:
        return templates.TemplateResponse(request, "methodology.html")

    return app


app = create_app(FileCardStore(cards_dir()))
