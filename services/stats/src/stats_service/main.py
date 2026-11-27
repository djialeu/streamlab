"""Service stats.

Au TD1, il CONSOMME ``system.ping`` dans le groupe ``stats-service`` et
expose le nombre de pings reçus. Au TD4, il agrégera les événements de lecture.
"""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from stats_service.config import Settings
from stats_service.ping_store import PingSnapshot, PingStore
from streamlab_contracts import SYSTEM_PING
from streamlab_kafka import ReceivedEvent, start_consumer

SERVICE_NAME = "stats"
LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"
logger = logging.getLogger(__name__)


def create_app(store: PingStore | None = None, start_kafka: bool = True) -> FastAPI:
    """Fabrique l'application.

    ``start_kafka=False`` permet de tester l'API sans broker Kafka.
    """
    ping_store = store or PingStore()

    def handle_ping(received: ReceivedEvent) -> None:
        """Appelé par le thread du consommateur pour chaque ping valide."""
        if ping_store.record(received):
            logger.info(
                "Ping reçu eventId=%s partition=%s offset=%s",
                received.event.event_id,
                received.partition,
                received.offset,
            )
        else:
            logger.info("Doublon ignoré eventId=%s", received.event.event_id)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Avec --reload, l'application tourne dans un processus enfant :
        # les logs sont donc configurés ici et non dans __main__.
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        consumer = None
        if start_kafka:
            settings = Settings()
            consumer = start_consumer(
                brokers=settings.kafka_brokers,
                group_id=settings.consumer_group,
                topics=[SYSTEM_PING],
                handler=handle_ping,
            )
        logger.info("Service %s démarré", SERVICE_NAME)
        yield
        # Arrêt (Ctrl+C / SIGTERM) : on ferme le consommateur, qui commite
        # et quitte le groupe proprement.
        if consumer is not None:
            consumer.stop()
        logger.info("Service %s arrêté proprement", SERVICE_NAME)

    app = FastAPI(title="StreamLab — stats", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Sonde de vie : le service répond."""
        return {"status": "ok", "service": SERVICE_NAME}

    @app.get("/stats/pings")
    async def stats_pings() -> PingSnapshot:
        """Nombre de pings reçus et dernier événement (avec partition et offset)."""
        return ping_store.snapshot()

    return app


# Application utilisée par uvicorn ("stats_service.main:app").
app = create_app()
