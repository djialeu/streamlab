"""Tests du compteur de pings : idempotence et état exposé."""

from stats_service.ping_store import PingStore
from streamlab_contracts import SYSTEM_PING, SystemPingPayload, create_event, parse_event
from streamlab_kafka import ReceivedEvent


def received(partition: int = 0, offset: int = 0, message: str = "ping") -> ReceivedEvent:
    event = create_event(SYSTEM_PING, SystemPingPayload(message=message), source="test")
    # Comme en production : l'événement reçu sort de parse_event.
    return ReceivedEvent(
        event=parse_event(event.to_json()), topic=SYSTEM_PING, partition=partition, offset=offset
    )


def test_etat_initial_vide() -> None:
    snapshot = PingStore().snapshot()

    assert snapshot.count == 0
    assert snapshot.duplicates_ignored == 0
    assert snapshot.last_event is None


def test_compte_les_pings_et_garde_le_dernier() -> None:
    store = PingStore()
    store.record(received(partition=0, offset=3))
    last = received(partition=2, offset=9, message="dernier")
    store.record(last)

    snapshot = store.snapshot()

    assert snapshot.count == 2
    assert snapshot.last_event is not None
    assert snapshot.last_event.event_id == last.event.event_id
    assert snapshot.last_event.partition == 2
    assert snapshot.last_event.offset == 9
    assert snapshot.last_event.message == "dernier"


def test_idempotent_un_event_id_deja_vu_est_ignore() -> None:
    store = PingStore()
    ping = received()

    assert store.record(ping) is True
    # Même événement relu (ex. après un redémarrage avant le commit).
    assert store.record(ping) is False

    snapshot = store.snapshot()
    assert snapshot.count == 1
    assert snapshot.duplicates_ignored == 1
