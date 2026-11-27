"""Enveloppe commune à tous les événements Kafka de StreamLab.

Tout message publié sur Kafka a la même forme JSON (champs en camelCase) :

    {
      "eventId": "...uuid v4...",
      "type": "system.ping",
      "version": 1,
      "occurredAt": "2026-11-27T14:00:00.000Z",
      "source": "catalog",
      "payload": { ... propre à chaque type ... }
    }

- ``create_event`` fabrique une enveloppe à publier ;
- ``parse_event`` valide un message reçu en DEUX temps : l'enveloppe, puis
  le payload selon le couple (type, version) enregistré dans le registre.
"""

import uuid
from datetime import UTC, datetime
from typing import Any

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel


class EventModel(BaseModel):
    """Base des modèles d'événements.

    - ``alias_generator=to_camel`` : ``event_id`` en Python <-> ``eventId`` en JSON ;
    - ``validate_by_name`` : on peut aussi construire avec les noms Python ;
    - ``frozen`` : un événement est un fait passé, il ne se modifie pas ;
    - ``extra="forbid"`` : un champ inconnu est une erreur (contrat strict).
    """

    model_config = ConfigDict(
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        frozen=True,
        extra="forbid",
    )


class EventEnvelope[PayloadT: BaseModel](EventModel):
    """Enveloppe d'un événement dont le payload est de type ``PayloadT``."""

    event_id: uuid.UUID
    type: str = Field(min_length=1)
    version: int = Field(ge=1)
    # AwareDatetime : une date SANS fuseau horaire est refusée.
    occurred_at: AwareDatetime
    source: str = Field(min_length=1)
    payload: PayloadT

    def to_json(self) -> str:
        """Sérialise l'événement en JSON (camelCase, date ISO 8601 en UTC)."""
        return self.model_dump_json()


class _RawEnvelope(EventEnvelope[Any]):
    """Enveloppe dont le payload n'est pas encore validé (1re étape de parse_event)."""

    payload: dict[str, Any]


class InvalidEventError(ValueError):
    """Levée quand un message ne respecte pas le contrat d'événement."""


# Registre (type, version) -> modèle du payload. Rempli par register_event().
_PAYLOAD_MODELS: dict[tuple[str, int], type[BaseModel]] = {}


def register_event(event_type: str, version: int, payload_model: type[BaseModel]) -> None:
    """Enregistre le schéma de payload d'un type d'événement dans une version donnée."""
    key = (event_type, version)
    if key in _PAYLOAD_MODELS:
        raise ValueError(f"Événement déjà enregistré : {event_type} v{version}")
    _PAYLOAD_MODELS[key] = payload_model


def create_event[PayloadT: BaseModel](
    event_type: str,
    payload: PayloadT,
    source: str,
    version: int = 1,
) -> EventEnvelope[PayloadT]:
    """Fabrique un nouvel événement : identifiant unique et date courante en UTC."""
    return EventEnvelope[PayloadT](
        event_id=uuid.uuid4(),
        type=event_type,
        version=version,
        occurred_at=datetime.now(UTC),
        source=source,
        payload=payload,
    )


def parse_event(raw: str | bytes) -> EventEnvelope[BaseModel]:
    """Valide un message JSON reçu et renvoie l'événement typé.

    Lève ``InvalidEventError`` si le JSON est illisible, si l'enveloppe est
    invalide, si le couple (type, version) est inconnu ou si le payload est
    invalide. Le consommateur décide quoi en faire (journaliser et ignorer).
    """
    # 1) L'enveloppe : champs communs, payload encore brut.
    try:
        envelope = _RawEnvelope.model_validate_json(raw)
    except ValidationError as error:
        raise InvalidEventError(f"Enveloppe invalide : {_describe(error)}") from error

    # 2) Le payload, selon le schéma enregistré pour (type, version).
    payload_model = _PAYLOAD_MODELS.get((envelope.type, envelope.version))
    if payload_model is None:
        raise InvalidEventError(f"Type d'événement inconnu : {envelope.type} v{envelope.version}")
    try:
        payload = payload_model.model_validate(envelope.payload)
    except ValidationError as error:
        raise InvalidEventError(f"payload invalide : {_describe(error)}") from error

    return EventEnvelope[BaseModel](
        event_id=envelope.event_id,
        type=envelope.type,
        version=envelope.version,
        occurred_at=envelope.occurred_at,
        source=envelope.source,
        payload=payload,
    )


def _describe(error: ValidationError) -> str:
    """Résume une erreur Pydantic en une ligne lisible : « champ: message ; ... »."""
    return " ; ".join(
        f"{'.'.join(str(part) for part in issue['loc']) or '(racine)'}: {issue['msg']}"
        for issue in error.errors()
    )
