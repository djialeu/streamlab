"""Tests du traitement d'un message reçu, sans broker Kafka.

``process_message`` est séparée de la boucle de consommation justement pour
être testable avec un faux message.
"""

import logging
from dataclasses import dataclass

import pytest

from streamlab_contracts import SYSTEM_PING, SystemPingPayload, create_event
from streamlab_kafka import ReceivedEvent, process_message


@dataclass
class FakeMessage:
    """Imite l'interface de confluent_kafka.Message utilisée par process_message."""

    payload: bytes | None
    partition_number: int = 1
    offset_number: int = 42

    def value(self) -> bytes | None:
        return self.payload

    def topic(self) -> str:
        return SYSTEM_PING

    def partition(self) -> int:
        return self.partition_number

    def offset(self) -> int:
        return self.offset_number


def test_message_valide_transmis_au_handler_avec_partition_et_offset() -> None:
    event = create_event(SYSTEM_PING, SystemPingPayload(message="salut"), source="test")
    received: list[ReceivedEvent] = []

    handled = process_message(FakeMessage(event.to_json().encode()), received.append)

    assert handled is True
    assert len(received) == 1
    assert received[0].event == event
    assert received[0].topic == SYSTEM_PING
    assert received[0].partition == 1
    assert received[0].offset == 42


@pytest.mark.parametrize(
    "payload",
    [
        b"pas du json",
        b'{"type": "system.ping"}',
        None,  # message vide (tombstone)
    ],
)
def test_message_invalide_journalise_puis_ignore(
    payload: bytes | None, caplog: pytest.LogCaptureFixture
) -> None:
    received: list[ReceivedEvent] = []

    with caplog.at_level(logging.WARNING):
        handled = process_message(FakeMessage(payload), received.append)

    assert handled is False
    assert received == []
    assert "ignoré" in caplog.text
    assert "partition=1" in caplog.text
    assert "offset=42" in caplog.text
