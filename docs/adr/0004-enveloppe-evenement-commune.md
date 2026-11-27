# ADR 0004 — Enveloppe d'événement commune, validation Pydantic, consommateurs idempotents

- **Statut** : accepté
- **Date** : 2026-11-27
- **TD concerné** : TD1

## Contexte

Avec 15 groupes qui produisent et consomment des événements, il faut :
- une forme **prévisible** pour tous les messages (journaux, débogage, Kafbat UI) ;
- pouvoir **faire évoluer** un payload sans casser les consommateurs existants ;
- **détecter tôt** un message mal formé, sans bloquer une partition ;
- supporter la livraison « au moins une fois » de Kafka (doublons possibles).

## Options envisagées

### Option A — Payload brut, propre à chaque topic
- Inconvénients : rien de commun (identifiant, date, version) ; chaque consommateur réinvente la déduplication et la validation.

### Option B — Avro ou Protobuf avec un registre de schémas
- Avantages : schémas formels, compatibilité vérifiée par le registre.
- Inconvénients : infrastructure et outillage supplémentaires dès le TD1 ; moins lisible dans Kafbat UI ; prévu plus tard comme **module de groupe**.

### Option C — Enveloppe JSON commune + schémas Pydantic partagés (retenue)
- JSON lisible partout ; validation à l'exécution par Pydantic v2 ; contrats dans un paquet partagé (`packages/contracts`).

## Décision

**Option C.**

- Enveloppe : `eventId` (UUID v4), `type`, `version` (≥ 1), `occurredAt` (ISO 8601 avec fuseau, UTC), `source`, `payload`. JSON en camelCase.
- `create_event()` pour produire ; `parse_event()` pour consommer, qui valide **l'enveloppe, puis le payload** selon le registre `(type, version) → modèle`, et lève `InvalidEventError`.
- Contrat **strict** (`extra="forbid"`) et modèles **figés** (`frozen=True`).
- Un changement incompatible donne une **nouvelle `version`** ; l'ancienne reste enregistrée.
- Consommateurs : message invalide **journalisé puis ignoré** (offset commité) ; commit **après** traitement ; traitement **idempotent par `eventId`**.

## Conséquences

- **Positives** : contrats uniques et testés ; la déduplication s'appuie sur un champ garanti ; versionnage explicite ; messages lisibles dans Kafbat UI.
- **Négatives** : JSON plus volumineux qu'un format binaire ; compatibilité vérifiée par les tests, pas par un registre ; avec un contrat strict, ajouter un champ demande une nouvelle version.
- **À revoir** : TD6 (DLQ à la place de « journaliser et ignorer », outbox côté producteur) ; module « registre de schémas » ; tests de contrat au TD5.
