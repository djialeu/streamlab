"""Service catalog.

Au TD1, il ne gère pas encore de catalogue (TD2) : il sert à PUBLIER un
événement de test ``system.ping`` sur Kafka via ``POST /dev/ping``.
"""

import asyncio
import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Protocol

from fastapi import FastAPI, HTTPException, Request, status
from pydantic import BaseModel, Field

from catalog_service.config import Settings
from streamlab_contracts import (
    SYSTEM_PING,
    EventEnvelope,
    EventModel,
    SystemPingPayload,
    create_event,
)
from streamlab_kafka import DeliveryResult, create_publisher

SERVICE_NAME = "catalog"
LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"
logger = logging.getLogger(__name__)


class EventPublisher(Protocol):
    """Ce dont le service a besoin pour publier (le vrai Publisher ou un faux en test)."""

    def publish[PayloadT: BaseModel](
        self, topic: str, event: EventEnvelope[PayloadT], key: str
    ) -> DeliveryResult: ...
    def close(self) -> None: ...


class PingRequest(BaseModel):
    """Corps (facultatif) de POST /dev/ping."""

    message: str = Field(default="ping", min_length=1, max_length=200)
    # Clé Kafka : même clé => même partition. Par défaut : l'eventId.
    key: str | None = Field(default=None, min_length=1, max_length=100)


class PingResponse(EventModel):
    """Réponse de POST /dev/ping (JSON en camelCase : eventId...)."""

    event_id: str
    topic: str
    partition: int
    offset: int


def create_app(publisher: EventPublisher | None = None) -> FastAPI:
    """Fabrique l'application.

    ``publisher`` permet aux tests d'injecter un faux publisher. Sinon, un
    vrai publisher Kafka est créé au démarrage (lifespan).
    """

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        # Avec --reload, l'application tourne dans un processus enfant :
        # les logs sont donc configurés ici et non dans __main__.
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        if publisher is None:
            settings = Settings()
            app.state.publisher = create_publisher(settings.kafka_brokers, SERVICE_NAME)
        else:
            app.state.publisher = publisher
        logger.info("Service %s démarré", SERVICE_NAME)
        yield
        # Arrêt (Ctrl+C / SIGTERM) : on envoie les derniers messages en attente.
        app.state.publisher.close()
        logger.info("Service %s arrêté proprement", SERVICE_NAME)

    app = FastAPI(title="StreamLab — catalog", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Sonde de vie : le service répond."""
        return {"status": "ok", "service": SERVICE_NAME}

    @app.post("/dev/ping", status_code=status.HTTP_202_ACCEPTED)
    async def dev_ping(request: Request, body: PingRequest | None = None) -> PingResponse:
        """Publie un événement ``system.ping`` (route de développement).

        202 Accepted : l'événement est bien dans Kafka, mais son traitement
        par les consommateurs (stats) se fera plus tard, de façon asynchrone.
        """
        body = body or PingRequest()
        event = create_event(
            SYSTEM_PING, SystemPingPayload(message=body.message), source=SERVICE_NAME
        )
        key = body.key or str(event.event_id)
        event_publisher: EventPublisher = request.app.state.publisher
        try:
            # publish() attend Kafka (appel bloquant) : on l'exécute dans un
            # thread pour ne pas geler la boucle async du serveur.
            result = await asyncio.to_thread(event_publisher.publish, SYSTEM_PING, event, key)
        except Exception as error:
            logger.exception("Publication impossible")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Kafka indisponible : {error}",
            ) from error
        return PingResponse(
            event_id=str(event.event_id),
            topic=result.topic,
            partition=result.partition,
            offset=result.offset,
        )

    return app


# Application utilisée par uvicorn ("catalog_service.main:app").
app = create_app()
