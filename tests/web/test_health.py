from fastapi.testclient import TestClient

from panorama_web.app import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_api_docs_are_hidden():
    assert client.get("/docs").status_code == 404
    assert client.get("/openapi.json").status_code == 404
