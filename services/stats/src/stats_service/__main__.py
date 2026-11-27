"""Point d'entrée : ``python -m stats_service [--reload]``.

uvicorn gère SIGINT (Ctrl+C) et SIGTERM : il termine les requêtes en cours
puis exécute la fin du lifespan (arrêt propre).
"""

import io
import os
import sys

import uvicorn

from stats_service.config import Settings


def use_utf8_output() -> None:
    """Force l'UTF-8 sur la console (sous Windows, les accents s'afficheraient mal).

    PYTHONUTF8 est hérité par le processus enfant lancé par --reload.
    """
    os.environ.setdefault("PYTHONUTF8", "1")
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def main() -> None:
    use_utf8_output()
    settings = Settings()
    uvicorn.run(
        "stats_service.main:app",
        host=settings.host,
        port=settings.port,
        reload="--reload" in sys.argv,
    )


if __name__ == "__main__":
    main()
