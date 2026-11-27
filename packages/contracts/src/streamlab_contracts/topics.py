"""Noms des topics Kafka de StreamLab.

Convention : ``<domaine>.<événement au passé>`` (ex. ``video.uploaded``).
Chaque nom est déclaré UNE SEULE FOIS ici : les services importent ces
constantes au lieu d'écrire les noms en dur (une faute de frappe devient
alors une erreur visible à l'import, pas un message perdu).

Ajouter un topic : ADR dans docs/adr/, puis ici, puis dans
infra/kafka/create-topics.sh.
"""

from typing import Final

# TD1 : topic de test qui prouve qu'un événement traverse Kafka.
SYSTEM_PING: Final = "system.ping"

# Liste de tous les topics connus (utilisée par les tests de convention).
ALL_TOPICS: Final[tuple[str, ...]] = (SYSTEM_PING,)
