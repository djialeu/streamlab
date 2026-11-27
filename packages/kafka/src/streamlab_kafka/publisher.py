"""Publication d'événements sur Kafka avec un producteur idempotent."""

import logging
from dataclasses import dataclass

from confluent_kafka import KafkaError, KafkaException, Message, Producer
from pydantic import BaseModel

from streamlab_contracts import EventEnvelope

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class DeliveryResult:
    """Où Kafka a écrit le message : partition et position (offset)."""

    topic: str
    partition: int
    offset: int


class Publisher:
    """Publie des événements StreamLab sur Kafka.

    Utiliser ``create_publisher`` plutôt que le constructeur.
    """

    def __init__(self, producer: Producer, delivery_timeout_s: float = 10.0) -> None:
        self._producer = producer
        self._delivery_timeout_s = delivery_timeout_s

    def publish(self, topic: str, event: EventEnvelope[BaseModel], key: str) -> DeliveryResult:
        """Publie un événement et ATTEND l'accusé de réception de Kafka.

        La clé détermine la partition (hash(clé) % nombre de partitions) :
        tous les messages de même clé arrivent dans la même partition, donc
        dans l'ordre.

        Appel BLOQUANT (jusqu'à ``delivery_timeout_s``) : depuis du code
        async, l'appeler via ``asyncio.to_thread(publisher.publish, ...)``.
        Attendre chaque message est lent à grande échelle, mais simple et
        suffisant ici : on obtient tout de suite la partition et l'offset.
        """
        results: list[DeliveryResult] = []
        errors: list[KafkaError] = []

        def on_delivery(error: KafkaError | None, message: Message) -> None:
            # Appelé par librdkafka (pendant flush) quand Kafka a répondu.
            if error is not None:
                errors.append(error)
                return
            results.append(
                DeliveryResult(
                    topic=message.topic() or topic,
                    partition=message.partition() or 0,
                    offset=message.offset() or 0,
                )
            )

        self._producer.produce(
            topic,
            key=key.encode(),
            value=event.to_json().encode(),
            on_delivery=on_delivery,
        )
        # flush() envoie les messages en attente et déclenche les callbacks.
        remaining = self._producer.flush(self._delivery_timeout_s)

        if errors:
            raise KafkaException(errors[0])
        if remaining > 0 or not results:
            raise TimeoutError(
                f"Kafka n'a pas confirmé la publication sur {topic} "
                f"en {self._delivery_timeout_s} s (broker joignable ?)"
            )
        result = results[0]
        logger.info(
            "Événement publié type=%s eventId=%s partition=%s offset=%s",
            event.type,
            event.event_id,
            result.partition,
            result.offset,
        )
        return result

    def close(self) -> None:
        """Envoie les derniers messages en attente avant l'arrêt du service."""
        self._producer.flush(self._delivery_timeout_s)


def create_publisher(brokers: str, client_id: str) -> Publisher:
    """Crée un publisher avec un producteur IDEMPOTENT.

    ``enable.idempotence`` : si un envoi est réessayé après une coupure
    réseau, le broker reconnaît le doublon et ne l'écrit qu'une fois.
    Cela implique ``acks=all`` et préserve l'ordre par partition.
    """
    producer = Producer(
        {
            "bootstrap.servers": brokers,
            "client.id": client_id,
            "enable.idempotence": True,
        }
    )
    return Publisher(producer)
