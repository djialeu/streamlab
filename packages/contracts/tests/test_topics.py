"""Tests de la convention de nommage des topics."""

import re

from streamlab_contracts import ALL_TOPICS, SYSTEM_PING

# <domaine>.<événement au passé> en minuscules (system.ping est l'exception du TD1).
TOPIC_NAME = re.compile(r"^[a-z]+(\.[a-z]+)+$")


def test_system_ping_existe() -> None:
    assert SYSTEM_PING == "system.ping"


def test_tous_les_topics_respectent_la_convention() -> None:
    for topic in ALL_TOPICS:
        assert TOPIC_NAME.match(topic), topic


def test_pas_de_doublon() -> None:
    assert len(ALL_TOPICS) == len(set(ALL_TOPICS))
