"""Compteur des pings reçus, en mémoire (pas de base au TD1).

IDEMPOTENCE : Kafka livre « au moins une fois », un même événement peut
donc être relu (redémarrage avant commit, rééquilibrage du groupe). On
mémorise les ``eventId`` déjà traités et on ignore les doublons.

CONCURRENCE : le thread du consommateur Kafka écrit pendant que les
requêtes HTTP lisent. Un verrou (``threading.Lock``) protège l'état.

Limites assumées au TD1 : l'état est perdu au redémarrage et l'ensemble
des eventId grandit sans fin. Une base PostgreSQL prendra le relais au TD4.
"""

import threading
import uuid
from datetime import UTC, datetime

from streamlab_contracts import EventModel, SystemPingPayload
from streamlab_kafka import ReceivedEvent


class LastPing(EventModel):
    """Dernier ping reçu, avec sa position dans Kafka (JSON en camelCase)."""

    event_id: uuid.UUID
    source: str
    message: str
    occurred_at: datetime
    received_at: datetime
    topic: str
    partition: int
    offset: int


class PingSnapshot(EventModel):
    """État exposé par GET /stats/pings."""

    count: int
    duplicates_ignored: int
    last_event: LastPing | None


class PingStore:
    """Compte les pings de façon idempotente et thread-safe."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._seen_event_ids: set[uuid.UUID] = set()
        self._duplicates_ignored = 0
        self._last: LastPing | None = None

    def record(self, received: ReceivedEvent) -> bool:
        """Enregistre un ping. Renvoie ``False`` si son eventId était déjà connu."""
        event = received.event
        with self._lock:
            if event.event_id in self._seen_event_ids:
                self._duplicates_ignored += 1
                return False
            self._seen_event_ids.add(event.event_id)
            message = event.payload.message if isinstance(event.payload, SystemPingPayload) else ""
            self._last = LastPing(
                event_id=event.event_id,
                source=event.source,
                message=message,
                occurred_at=event.occurred_at,
                received_at=datetime.now(UTC),
                topic=received.topic,
                partition=received.partition,
                offset=received.offset,
            )
            return True

    def snapshot(self) -> PingSnapshot:
        """Copie cohérente de l'état courant."""
        with self._lock:
            return PingSnapshot(
                count=len(self._seen_event_ids),
                duplicates_ignored=self._duplicates_ignored,
                last_event=self._last,
            )
