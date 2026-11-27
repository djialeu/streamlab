"""Consommation d'événements Kafka dans un groupe de consommateurs.

Principes (voir AGENTS.md) :
- chaque message est validé avec ``parse_event`` ;
- un message invalide est journalisé puis ignoré : il ne bloque jamais
  la partition (sinon il serait relu en boucle : « poison pill ») ;
- l'offset est commité APRÈS le traitement : livraison « au moins une
  fois », donc le handler doit être idempotent.
"""

import logging
import threading
from collections.abc import Callable
from dataclasses import dataclass
from typing import Protocol

from confluent_kafka import Consumer, KafkaError
from pydantic import BaseModel

from streamlab_contracts import EventEnvelope, InvalidEventError, parse_event

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ReceivedEvent:
    """Un événement validé, avec sa position dans Kafka."""

    event: EventEnvelope[BaseModel]
    topic: str
    partition: int
    offset: int


EventHandler = Callable[[ReceivedEvent], None]


class KafkaMessage(Protocol):
    """Partie de ``confluent_kafka.Message`` dont on a besoin (facilite les tests)."""

    def value(self) -> bytes | None: ...
    def topic(self) -> str | None: ...
    def partition(self) -> int | None: ...
    def offset(self) -> int | None: ...


def process_message(message: KafkaMessage, handler: EventHandler) -> bool:
    """Valide un message reçu puis le transmet au handler.

    Renvoie ``True`` si le message a été transmis, ``False`` s'il était
    invalide (il est alors journalisé puis ignoré).
    """
    topic = message.topic() or "?"
    partition = message.partition()
    offset = message.offset()
    raw = message.value()

    if raw is None:
        logger.warning(
            "Message vide ignoré topic=%s partition=%s offset=%s", topic, partition, offset
        )
        return False
    try:
        event = parse_event(raw)
    except InvalidEventError as error:
        logger.warning(
            "Message invalide ignoré topic=%s partition=%s offset=%s : %s",
            topic,
            partition,
            offset,
            error,
        )
        return False

    handler(ReceivedEvent(event=event, topic=topic, partition=partition or 0, offset=offset or 0))
    return True


class RunningConsumer:
    """Un consommateur qui tourne dans son propre thread. Arrêt : ``stop()``."""

    def __init__(
        self, consumer: Consumer, topics: list[str], handler: EventHandler, group_id: str
    ) -> None:
        self._consumer = consumer
        self._topics = topics
        self._handler = handler
        self._group_id = group_id
        self._stop_requested = threading.Event()
        # Thread « daemon » : il ne bloque pas la sortie du programme en cas d'urgence.
        self._thread = threading.Thread(
            target=self._run, name=f"kafka-consumer-{group_id}", daemon=True
        )

    def start(self) -> None:
        self._thread.start()

    def _run(self) -> None:
        """Boucle de consommation : poll -> traitement -> commit."""
        self._consumer.subscribe(self._topics)
        logger.info("Consommateur démarré groupe=%s topics=%s", self._group_id, self._topics)
        try:
            while not self._stop_requested.is_set():
                # poll() attend au plus 0,5 s : la boucle vérifie régulièrement
                # si un arrêt a été demandé.
                message = self._consumer.poll(0.5)
                if message is None:
                    continue
                error = message.error()
                if error is not None:
                    # Erreur côté Kafka (pas un message) : on la signale et on continue.
                    if error.code() != KafkaError._PARTITION_EOF:
                        logger.error("Erreur Kafka : %s", error.str())
                    continue
                try:
                    process_message(message, self._handler)
                except Exception:
                    # Bug dans le handler : on journalise sans tuer le consommateur.
                    logger.exception(
                        "Échec du traitement partition=%s offset=%s",
                        message.partition(),
                        message.offset(),
                    )
                # Commit APRÈS traitement (valide ou non) : la partition avance.
                self._consumer.commit(message=message, asynchronous=False)
        finally:
            # close() commite et quitte le groupe proprement : les partitions
            # sont réattribuées tout de suite aux autres membres du groupe.
            self._consumer.close()
            logger.info("Consommateur arrêté groupe=%s", self._group_id)

    def stop(self, timeout_s: float = 10.0) -> None:
        """Demande l'arrêt et attend la fin de la boucle."""
        self._stop_requested.set()
        self._thread.join(timeout_s)


def start_consumer(
    brokers: str,
    group_id: str,
    topics: list[str],
    handler: EventHandler,
) -> RunningConsumer:
    """Démarre un consommateur dans le groupe ``group_id`` (dans un thread).

    - ``auto.offset.reset=earliest`` : un groupe tout neuf lit depuis le début ;
    - ``enable.auto.commit=False`` : on commite nous-mêmes, après traitement.
    """
    consumer = Consumer(
        {
            "bootstrap.servers": brokers,
            "group.id": group_id,
            "auto.offset.reset": "earliest",
            "enable.auto.commit": False,
        }
    )
    running = RunningConsumer(consumer, topics, handler, group_id)
    running.start()
    return running
