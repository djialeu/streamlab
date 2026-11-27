"""Tests du contrat d'événement : création, sérialisation et validation."""

import json
import uuid
from datetime import UTC, datetime

import pytest

from streamlab_contracts import (
    SYSTEM_PING,
    InvalidEventError,
    SystemPingPayload,
    create_event,
    parse_event,
)


def make_ping_json(**overrides: object) -> bytes:
    """Construit un ping valide sous forme JSON, avec des champs modifiables."""
    data: dict[str, object] = {
        "eventId": str(uuid.uuid4()),
        "type": "system.ping",
        "version": 1,
        "occurredAt": "2026-11-27T14:00:00.000Z",
        "source": "catalog",
        "payload": {"message": "bonjour"},
    }
    data.update(overrides)
    return json.dumps(data).encode()


class TestCreateEvent:
    def test_remplit_les_champs_de_l_enveloppe(self) -> None:
        event = create_event(SYSTEM_PING, SystemPingPayload(message="bonjour"), source="catalog")

        assert isinstance(event.event_id, uuid.UUID)
        assert event.event_id.version == 4
        assert event.type == "system.ping"
        assert event.version == 1
        assert event.source == "catalog"
        assert event.payload == SystemPingPayload(message="bonjour")

    def test_occurred_at_est_en_utc(self) -> None:
        event = create_event(SYSTEM_PING, SystemPingPayload(message="x"), source="catalog")

        assert event.occurred_at.tzinfo is not None
        assert event.occurred_at.utcoffset() == UTC.utcoffset(None)

    def test_deux_evenements_ont_des_identifiants_differents(self) -> None:
        a = create_event(SYSTEM_PING, SystemPingPayload(message="x"), source="catalog")
        b = create_event(SYSTEM_PING, SystemPingPayload(message="x"), source="catalog")

        assert a.event_id != b.event_id

    def test_serialise_en_camel_case(self) -> None:
        event = create_event(SYSTEM_PING, SystemPingPayload(message="x"), source="catalog")

        data = json.loads(event.to_json())

        assert set(data) == {"eventId", "type", "version", "occurredAt", "source", "payload"}
        assert data["occurredAt"].endswith("Z")


class TestParseEvent:
    def test_aller_retour_create_puis_parse(self) -> None:
        original = create_event(SYSTEM_PING, SystemPingPayload(message="aller-retour"), "catalog")

        parsed = parse_event(original.to_json())

        assert parsed == original
        assert isinstance(parsed.payload, SystemPingPayload)

    def test_accepte_un_json_valide(self) -> None:
        parsed = parse_event(make_ping_json())

        assert parsed.type == "system.ping"
        assert parsed.occurred_at == datetime(2026, 11, 27, 14, 0, tzinfo=UTC)
        assert isinstance(parsed.payload, SystemPingPayload)
        assert parsed.payload.message == "bonjour"

    def test_rejette_un_texte_qui_n_est_pas_du_json(self) -> None:
        with pytest.raises(InvalidEventError):
            parse_event(b"ceci n'est pas du JSON")

    def test_rejette_une_enveloppe_sans_event_id(self) -> None:
        data = json.loads(make_ping_json())
        del data["eventId"]

        with pytest.raises(InvalidEventError, match="eventId"):
            parse_event(json.dumps(data))

    @pytest.mark.parametrize(
        ("field", "value"),
        [
            ("eventId", "pas-un-uuid"),
            ("occurredAt", "hier"),
            ("version", 0),
            ("source", ""),
        ],
    )
    def test_rejette_un_champ_d_enveloppe_invalide(self, field: str, value: object) -> None:
        with pytest.raises(InvalidEventError):
            parse_event(make_ping_json(**{field: value}))

    def test_rejette_une_date_sans_fuseau_horaire(self) -> None:
        with pytest.raises(InvalidEventError):
            parse_event(make_ping_json(occurredAt="2026-11-27T14:00:00"))

    def test_rejette_un_type_inconnu(self) -> None:
        with pytest.raises(InvalidEventError, match="inconnu"):
            parse_event(make_ping_json(type="video.inexistant"))

    def test_rejette_une_version_inconnue(self) -> None:
        with pytest.raises(InvalidEventError, match="inconnu"):
            parse_event(make_ping_json(version=99))

    def test_rejette_un_payload_invalide(self) -> None:
        with pytest.raises(InvalidEventError, match="payload"):
            parse_event(make_ping_json(payload={"message": ""}))

    def test_rejette_un_payload_avec_champ_inattendu(self) -> None:
        with pytest.raises(InvalidEventError):
            parse_event(make_ping_json(payload={"message": "ok", "pirate": True}))
