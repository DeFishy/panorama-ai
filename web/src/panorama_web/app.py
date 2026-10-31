"""Точка входа FastAPI."""

from fastapi import FastAPI

# Сайт закрыт приглашениями, поэтому автодокументацию API наружу не отдаём.
app = FastAPI(title="Panorama AI", docs_url=None, redoc_url=None, openapi_url=None)


@app.get("/health")
def health() -> dict[str, str]:
    """Проверка живости процесса для мониторинга. Базу данных не опрашивает."""
    return {"status": "ok"}
