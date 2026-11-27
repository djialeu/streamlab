"""Service identity : squelette au TD1 (comptes, rôles et JWT arrivent au TD5)."""

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI

SERVICE_NAME = "identity"
LOG_FORMAT = "%(levelname)s [%(name)s] %(message)s"
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Fabrique l'application FastAPI du service."""

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncIterator[None]:
        # Avant yield : démarrage. Après yield : arrêt (SIGINT/SIGTERM via uvicorn).
        # Les logs sont configurés ici car, avec --reload, l'application tourne
        # dans un processus enfant qui n'exécute pas __main__.
        logging.basicConfig(level=logging.INFO, format=LOG_FORMAT)
        logger.info("Service %s démarré", SERVICE_NAME)
        yield
        logger.info("Service %s arrêté proprement", SERVICE_NAME)

    app = FastAPI(title="StreamLab — identity", version="0.1.0", lifespan=lifespan)

    @app.get("/health")
    async def health() -> dict[str, str]:
        """Sonde de vie : le service répond."""
        return {"status": "ok", "service": SERVICE_NAME}

    return app


# Application utilisée par uvicorn ("identity_service.main:app").
app = create_app()
