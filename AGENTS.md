# AGENTS.md — Règles pour les agents de code (et les humains)

Ce fichier est lu par **tous les agents de code** (Claude Code via `CLAUDE.md`, Codex, Cursor, Copilot…) avant toute intervention. Il s'applique aussi aux étudiants. En cas de doute, **demander plutôt que deviner**.

---

## 1. Le projet en bref

StreamLab est une plateforme de **streaming vidéo éducative** (YouTube et Twitch simplifiés), projet fil rouge du cours « Technologie web et applications » (M2 Génie logiciel). Six TD construisent un socle, puis 10 à 15 groupes ajoutent chacun un module dans **ce même dépôt**.

Le code est une **référence pédagogique** : lisible avant tout, commenté en français, sans complexité inutile.

Vision complète : [`docs/vision.md`](docs/vision.md). Parcours pédagogique pour (re)découvrir le projet : [`docs/guide-de-lecture.md`](docs/guide-de-lecture.md), **à compléter à la fin de chaque TD**. Architecture (C4, flux, événements, données) : [`docs/architecture/`](docs/architecture/README.md). Décisions : [`docs/adr/`](docs/adr/).

### Architecture cible (résumé)

```
Next.js (apps/web) ──REST──▶ Passerelle d'API ──REST──▶ Microservices FastAPI
                                                         │  (identity, catalog, upload,
                                                         │   transcoding, stats, modules…)
                                                         ├── 1 base PostgreSQL par service
                                                         └── événements Kafka entre services
Stockage objet S3 auto-hébergé (Garage/SeaweedFS) · FFmpeg (HLS) · MediaMTX (direct)
```

## 2. Pile technique

| Domaine | Outil | Version |
| --- | --- | --- |
| Orchestration du monorepo | pnpm workspaces + Turborepo | pnpm 12.23, turbo 2.11 |
| Environnement JS | Node.js | ≥ 24 (`.nvmrc`) |
| Services backend | Python + **FastAPI** + uvicorn | Python ≥ 3.12 |
| Validation | **Pydantic v2** (+ pydantic-settings pour la config) | |
| Workspace Python | **uv** (un seul `uv.lock`, un seul `.venv`) | uv ≥ 0.13 |
| Client Kafka | **`confluent-kafka`** (librdkafka) | 2.16 |
| Tests / types / lint | pytest · mypy `--strict` · ruff | |
| Broker | Apache Kafka 4 en mode **KRaft** (`apache/kafka:4.3.2`) | |
| Interface Kafka | Kafbat UI (`ghcr.io/kafbat/kafka-ui:v1.5.1`) | |
| Bases | PostgreSQL (`postgres:16-alpine`) | |

## 3. Structure du dépôt

```
apps/                 # interfaces (Next.js au TD2) — vide au TD1
packages/
  contracts/          # streamlab_contracts : topics, enveloppe d'événement, schémas de payload
  kafka/              # streamlab_kafka : publisher idempotent + consumer validant
services/
  catalog/            # catalog_service  — port 3001
  identity/           # identity_service — port 3002
  stats/              # stats_service    — port 3003
infra/
  kafka/create-topics.sh       # création des topics (conteneur kafka-init)
  postgres/init/               # une base + un utilisateur par service
scripts/smoke-test.mjs         # test de bout en bout (pnpm smoke)
docs/                          # vision, architecture, ADR
docker-compose.yml · .env.example · pyproject.toml (racine uv) · package.json (racine pnpm)
```

Chaque projet Python a :
- un `pyproject.toml` (dépendances, paquet dans `src/<nom>/`) ;
- un petit `package.json` dont les scripts (`dev`, `typecheck`, `lint`, `test`) appellent `uv run …`, pour que Turborepo l'orchestre comme les projets JS.

## 4. Commandes

| Commande | Effet |
| --- | --- |
| `pnpm install --prefer-offline` | Installe turbo (JS) |
| `pnpm setup` | `uv sync --all-packages` : crée `.venv` et installe tous les projets Python |
| `pnpm infra:up` / `infra:down` | Démarre / arrête Kafka, kafka-init, Kafbat UI, PostgreSQL |
| `pnpm infra:reset` | Supprime les volumes (données Kafka et Postgres) puis redémarre |
| `pnpm infra:logs` | Suit les journaux des conteneurs |
| `pnpm dev` | Lance les trois services (uvicorn, rechargement auto) |
| `pnpm typecheck` · `pnpm lint` · `pnpm test` | mypy · ruff · pytest dans tous les projets |
| `pnpm smoke` | Test de bout en bout : santé des services, ping catalog → Kafka → stats |

Dans un seul projet : `cd services/stats && uv run pytest`.

## 5. Conventions

### Topics Kafka
- Nom : **`<domaine>.<événement au passé>`**, en minuscules : `video.uploaded`, `user.registered`. Exception pédagogique : `system.ping` (topic de test du TD1).
- Les noms sont déclarés **une seule fois** dans `packages/contracts/src/streamlab_contracts/topics.py`, jamais en dur ailleurs.
- La **création automatique des topics est désactivée** : un topic est créé dans `infra/kafka/create-topics.sh`, **après un ADR**.

### Enveloppe d'événement
Tout message Kafka est une enveloppe JSON (champs en *camelCase*) :

```json
{
  "eventId": "uuid v4",
  "type": "system.ping",
  "version": 1,
  "occurredAt": "2026-11-27T14:00:00.000Z",
  "source": "catalog",
  "payload": { "message": "..." }
}
```

- Produire avec `create_event(...)`, lire avec `parse_event(...)`, qui valide l'enveloppe **puis** le payload selon `(type, version)`.
- Changement incompatible d'un payload : **nouvelle `version`**, l'ancienne reste lisible.
- La **clé** du message détermine la partition. On choisit une clé qui doit garder l'ordre (ex. `videoId`).

### Consommateurs idempotents
Kafka livre **au moins une fois** : un même message peut être relu (redémarrage, rééquilibrage). Tout consommateur doit donc être **idempotent**. Un `eventId` déjà traité est ignoré. Un message invalide est **journalisé puis ignoré** : il ne bloque jamais la partition.

### Une base par service
Chaque service possède **sa** base et **son** utilisateur PostgreSQL. Un service ne lit et n'écrit **jamais** la base d'un autre : il passe par son API REST ou par ses événements.

### Code
- Identifiants en **anglais**, commentaires et documentation en **français**.
- Typage complet (mypy strict), pas de `Any` sans justification.
- Configuration par variables d'environnement (`.env`, voir `.env.example`), jamais en dur.

## 6. Règles de travail

1. **Une branche et une PR par tâche.** Pas de commit direct sur `main`.
2. **Plan avant le code** : présenter le plan (fichiers touchés, approche) et le faire valider.
3. **Tests d'abord** : écrire ou adapter le test qui échoue, puis le code.
4. **Ne jamais supprimer ni affaiblir un test** pour le faire passer. Si un test semble faux, le signaler.
5. **Aucun secret ni donnée réelle** dans le dépôt (code, tests, fixtures, journaux). `.env` n'est jamais commité.
6. **Toute nouvelle dépendance** est vérifiée sur PyPI/npm (existence, dernière version, maintenance récente, licence libre) et justifiée dans la PR.
7. **Pas de nouveau topic, framework ou pattern sans ADR** dans `docs/adr/` (modèle : `0000-modele.md`).
8. **Économie de données** : ne jamais utiliser le tag `latest`, ni `docker compose pull`, ni `--pull always`. Utiliser `pnpm install --prefer-offline` et le cache uv.
9. Remplir le modèle de PR (`.github/pull_request_template.md`), y compris l'**usage de l'IA**.
10. Mettre à jour la **documentation** (README, `docs/architecture/`, ce fichier) dans la même PR que le code.

## 7. Feuille de route

| TD | Contenu | État |
| --- | --- | --- |
| **TD1** | Socle : monorepo, infra Docker, trois services squelettes, un événement de test qui traverse Kafka | **← étape en cours** |
| TD2 | Service catalogue avec sa base, passerelle d'API, interface Next.js | à venir |
| TD3 | Envoi et transcodage pilotés par événements (`video.uploaded` → workers → `video.transcoded`) | à venir |
| TD4 | Lecture adaptative et événements de lecture agrégés par stats | à venir |
| TD5 | Service identité, sécurité entre services, tests de contrat, CI bloquante | à venir |
| TD6 | Outbox, DLQ et reprises, déploiement, gabarit de module pour les groupes | à venir |

**Ne pas anticiper** les TD suivants : on code l'étape en cours, dans une structure qui accueillera la suite.
