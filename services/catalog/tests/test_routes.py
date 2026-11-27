"""Tests du service catalog, avec un faux publisher (aucun Kafka requis)."""

import uuid

from fastapi.testclient import TestClient
from pydantic import BaseModel

from catalog_service.main import create_app
from streamlab_contracts import SYSTEM_PING, EventEnvelope, SystemPingPayload, parse_event
from streamlab_kafka import DeliveryResult


class FakePublisher:
    """Enregistre les publications au lieu de les envoyer à Kafka."""

    def __init__(self) -> None:
        self.published: list[tuple[str, EventEnvelope[BaseModel], str]] = []
        self.closed = False

    def publish[PayloadT: BaseModel](
        self, topic: str, event: EventEnvelope[PayloadT], key: str
    ) -> DeliveryResult:
        # On relit l'événement comme le ferait un consommateur (contrat vérifié).
        self.published.append((topic, parse_event(event.to_json()), key))
        return DeliveryResult(topic=topic, partition=2, offset=7)

    def close(self) -> None:
        self.closed = True


def test_health() -> None:
    with TestClient(create_app(FakePublisher())) as client:
        response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "service": "catalog"}


def test_dev_ping_publie_un_system_ping() -> None:
    publisher = FakePublisher()
    with TestClient(create_app(publisher)) as client:
        response = client.post("/dev/ping", json={"message": "coucou"})

    assert response.status_code == 202
    body = response.json()
    assert body["topic"] == SYSTEM_PING
    assert body["partition"] == 2
    assert body["offset"] == 7

    topic, event, key = publisher.published[0]
    assert topic == SYSTEM_PING
    assert event.type == SYSTEM_PING
    assert event.source == "catalog"
    assert event.payload == SystemPingPayload(message="coucou")
    assert body["eventId"] == str(event.event_id)
    # Sans clé fournie, la clé est l'eventId : les pings se répartissent.
    assert key == str(event.event_id)


def test_dev_ping_sans_corps_utilise_un_message_par_defaut() -> None:
    publisher = FakePublisher()
    with TestClient(create_app(publisher)) as client:
        response = client.post("/dev/ping")

    assert response.status_code == 202
    uuid.UUID(response.json()["eventId"])
    assert publisher.published[0][1].payload == SystemPingPayload(message="ping")


def test_dev_ping_utilise_la_cle_fournie() -> None:
    publisher = FakePublisher()
    with TestClient(create_app(publisher)) as client:
        client.post("/dev/ping", json={"key": "meme-cle"})

    assert publisher.published[0][2] == "meme-cle"


def test_dev_ping_refuse_un_message_vide() -> None:
    publisher = FakePublisher()
    with TestClient(create_app(publisher)) as client:
        response = client.post("/dev/ping", json={"message": ""})

    assert response.status_code == 422
    assert publisher.published == []


def test_le_publisher_est_ferme_a_l_arret() -> None:
    publisher = FakePublisher()
    with TestClient(create_app(publisher)):
        pass

    assert publisher.closed is True
