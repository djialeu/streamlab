# Documentation d'architecture de StreamLab

Cette documentation décrit **l'état réel** du système, TD après TD. Pour la cible à long terme, voir [`docs/vision.md`](../vision.md). Pour le *pourquoi* des choix, voir les [ADR](../adr/).

> État actuel : **TD1 — socle**. Les éléments marqués *(prévu)* n'existent pas encore.

## Guide de lecture

| # | Document | Question à laquelle il répond | Public |
| --- | --- | --- | --- |
| 1 | [Contexte (C4 niveau 1)](01-contexte.md) | Qui utilise StreamLab, avec quels systèmes externes ? | Tout le monde |
| 2 | [Conteneurs (C4 niveau 2)](02-conteneurs.md) | Quelles applications, bases et flux composent le système ? | Développeurs, groupes |
| 3 | [Flux du ping (TD1)](03-flux-ping-td1.md) | Que se passe-t-il exactement quand un événement traverse Kafka ? | Développeurs |
| 4 | [Infrastructure locale](04-infrastructure-locale.md) | Comment Docker, Kafka (listeners), Postgres sont-ils configurés ? | Développeurs, dépannage |
| 5 | [Catalogue des événements](05-evenements.md) | Quels topics, quelle enveloppe, quelles règles ? | Tous les producteurs et consommateurs |
| 6 | [Données](06-donnees.md) | Qui possède quelle base ? Comment partager une donnée ? | Développeurs, groupes |

Ordre conseillé pour un nouvel arrivant : **1 → 2 → 5 → 3 → 4 → 6**.

## Conventions de ces documents

- Diagrammes en **Mermaid**, rendus directement par GitHub (et par l'aperçu Markdown de VS Code).
- Un document est **mis à jour dans la même PR** que le code qu'il décrit (règle d'AGENTS.md).
- Une décision structurante (nouveau topic, framework, pattern) fait l'objet d'un **ADR** dans [`docs/adr/`](../adr/).

## Décisions d'architecture (ADR)

| ADR | Décision |
| --- | --- |
| [0001](../adr/0001-microservices-et-kafka.md) | Microservices communiquant par événements Kafka |
| [0002](../adr/0002-monorepo-polyglotte-pnpm-turborepo-uv.md) | Monorepo polyglotte : pnpm + Turborepo (orchestration), uv (Python) |
| [0003](../adr/0003-client-kafka-confluent.md) | Client Kafka `confluent-kafka` (API synchrone stable) |
| [0004](../adr/0004-enveloppe-evenement-commune.md) | Enveloppe d'événement commune, validation Pydantic, consommateurs idempotents |
| [0005](../adr/0005-fastapi-pour-les-services.md) | FastAPI pour les services backend (plutôt que Django ou Fastify) |
