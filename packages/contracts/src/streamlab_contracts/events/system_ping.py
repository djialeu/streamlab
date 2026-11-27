"""Événement ``system.ping`` (TD1) : un simple message de test.

Il ne porte aucune donnée métier : il sert à prouver qu'un événement
publié par un service (catalog) traverse Kafka jusqu'à un autre (stats).
"""

from pydantic import Field

from streamlab_contracts.envelope import EventModel, register_event
from streamlab_contracts.topics import SYSTEM_PING


class SystemPingPayload(EventModel):
    """Payload de ``system.ping``, version 1."""

    message: str = Field(min_length=1, max_length=200)


register_event(SYSTEM_PING, 1, SystemPingPayload)
