"""Tests de l'API du service stats, sans consommateur Kafka."""

from fastapi.testclient import TestClient

from stats_service.main import create_app
from stats_service.ping_store import PingStore
from streamlab_contracts import SYSTEM_PING, SystemPingPayload, create_event, parse_event
from streamlab_kafka import ReceivedEvent


def test_health() -> None:
    with TestClient(create_app(PingStore(), start_kafka=False)) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "stats"}


def test_stats_pings_vide() -> None:
    with TestClient(create_app(PingStore(), start_kafka=False)) as client:
        response = client.get("/stats/pings")

    assert response.json() == {"count": 0, "duplicatesIgnored": 0, "lastEvent": None}


def test_stats_pings_expose_le_dernier_evenement() -> None:
    store = PingStore()
    event = create_event(SYSTEM_PING, SystemPingPayload(message="hello"), source="catalog")
    store.record(
        ReceivedEvent(event=parse_event(event.to_json()), topic=SYSTEM_PING, partition=1, offset=5)
    )

    with TestClient(create_app(store, start_kafka=False)) as client:
        body = client.get("/stats/pings").json()

    assert body["count"] == 1
    assert body["lastEvent"]["eventId"] == str(event.event_id)
    assert body["lastEvent"]["partition"] == 1
    assert body["lastEvent"]["offset"] == 5
    assert body["lastEvent"]["source"] == "catalog"
    assert body["lastEvent"]["message"] == "hello"
