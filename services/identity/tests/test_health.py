"""Tests du squelette identity."""

from fastapi.testclient import TestClient

from identity_service.main import create_app


def test_health() -> None:
    with TestClient(create_app()) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "identity"}
