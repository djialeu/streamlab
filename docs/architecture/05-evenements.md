# 5. Catalogue des événements

> **Question :** quels événements circulent, sous quelle forme, et quelles règles respecter pour en produire ou en consommer ?
> Source de vérité dans le code : [`packages/contracts`](../../packages/contracts/src/streamlab_contracts/).

## 5.1 Convention de nommage des topics

**`<domaine>.<événement au passé>`**, en minuscules, séparé par des points.

- Au passé, parce qu'un événement est un **fait accompli** (`video.uploaded`), pas un ordre (`upload.video`).
- On n'utilise que des points, jamais d'underscore : Kafka avertit que `.` et `_` peuvent entrer en collision dans les noms de métriques.
- Chaque nom est déclaré une seule fois dans [`topics.py`](../../packages/contracts/src/streamlab_contracts/topics.py). Un test vérifie la convention.

## 5.2 Topics

| Topic | Statut | Partitions | Producteur | Consommateurs (groupe) | Clé | Payload |
| --- | --- | --- | --- | --- | --- | --- |
| `system.ping` | **existe (TD1)** | 3 | catalog | stats (`stats-service`) | `eventId` par défaut, ou `key` fournie | `{ message: string (1-200) }` |
| `video.uploaded` | prévu TD3 | — | upload | transcoding | `videoId` | à définir (ADR) |
| `video.transcoded` | prévu TD3 | — | transcoding | catalog | `videoId` | à définir |
| `video.published` | prévu | — | catalog | à définir | `videoId` | à définir |
| `playback.events` | prévu TD4 | — | passerelle / lecteur | stats | `videoId` | à définir |
| `user.registered` | prévu TD5 | — | identity | à définir | `userId` | à définir |

Les topics prévus **ne sont pas créés** : chacun le sera avec son ADR, dans le TD concerné.

## 5.3 Enveloppe commune

Tout message est un JSON de cette forme :

```json
{
  "eventId": "3f050629-73c9-44dc-93b6-95f076c79208",
  "type": "system.ping",
  "version": 1,
  "occurredAt": "2026-11-27T14:03:52.933080Z",
  "source": "catalog",
  "payload": { "message": "premier ping" }
}
```

| Champ | Type | Règle | Sert à |
| --- | --- | --- | --- |
| `eventId` | UUID v4 | unique par événement | **idempotence** (déduplication) |
| `type` | chaîne | le nom du topic | choisir le schéma du payload |
| `version` | entier ≥ 1 | version du schéma du payload | faire évoluer un payload sans casser les consommateurs |
| `occurredAt` | date ISO 8601 **avec fuseau** | UTC à la création | dater le fait (≠ date de lecture) |
| `source` | chaîne non vide | nom du service producteur | traçabilité, débogage |
| `payload` | objet | validé selon `(type, version)` | données métier |

- **Produire** : `create_event(topic, PayloadModel(...), source="mon-service")`.
- **Consommer** : `parse_event(raw)` valide **l'enveloppe, puis le payload**. Elle lève `InvalidEventError` en cas d'échec.
- Les champs sont en **camelCase** en JSON et en **snake_case** en Python (`event_id`). Pydantic fait la conversion.
- Le contrat est **strict** (`extra="forbid"`) : un champ inattendu est une erreur.

## 5.4 Faire évoluer un événement

| Changement | Compatible ? | Que faire |
| --- | --- | --- |
| Ajouter un champ **optionnel** au payload | oui pour les nouveaux consommateurs, non pour les anciens (contrat strict) | nouvelle `version` |
| Renommer, supprimer, changer le type d'un champ | non | **nouvelle `version`** ; l'ancienne reste enregistrée tant qu'elle circule |
| Nouveau type d'événement | — | ADR, constante dans `topics.py`, module dans `events/`, `create-topics.sh` |

Un registre de schémas et des tests de contrat viendront plus tard (TD5 et modules).

## 5.5 Règles pour les consommateurs

1. **Rejoindre un groupe nommé d'après le service** (`stats-service`). Les instances d'un même service se partagent les partitions ; un autre service lit tout avec son propre groupe.
2. **Valider chaque message** avec `parse_event`.
3. **Message invalide : journaliser, puis ignorer** (et commiter). Il ne doit jamais bloquer la partition.
4. **Commiter après traitement.** La livraison est donc « au moins une fois ».
5. **Être idempotent** : un `eventId` déjà traité est ignoré.

La couche [`packages/kafka`](../../packages/kafka/src/streamlab_kafka/) applique déjà les règles 2 à 4 ; le service applique la règle 5.
