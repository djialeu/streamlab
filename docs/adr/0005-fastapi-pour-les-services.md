# ADR 0005 — FastAPI pour les services backend

- **Statut** : accepté
- **Date** : 2026-11-27
- **TD concerné** : TD1
- **Remarque** : cette décision **s'écarte du cahier des charges initial** (Node.js, TypeScript, Fastify 5, zod), à la demande de l'enseignant responsable.

## Contexte

Les services backend doivent être écrits en **Python**. Ils exposent de petites API JSON (santé, routes de développement, plus tard des API métier derrière une passerelle), publient et consomment des événements Kafka, et serviront de **code de référence** pour les étudiants. Le cahier des charges demande d'éviter la complexité inutile ; Django n'est envisageable que réduit au strict nécessaire.

## Options envisagées

### Option A — Django (+ Django REST Framework)
- Avantages : très complet (ORM, migrations, admin, authentification) ; très connu.
- Inconvénients : beaucoup de mécanismes inutiles pour des microservices qui n'exposent que du JSON (templates, admin, sessions) ; l'ORM et les migrations de Django imposent leur structure à chaque service ; l'asynchrone y est moins naturel ; un « Django minimal » demande de désactiver beaucoup de choses, ce qui est contraire à l'objectif de lisibilité.

### Option B — Flask
- Avantages : minimal, simple.
- Inconvénients : pas de validation ni d'OpenAPI intégrées (il faut des extensions) ; synchrone.

### Option C — FastAPI (retenue)
- Avantages : léger, n'impose ni ORM ni structure ; **validation par Pydantic v2** (déjà utilisé pour les contrats d'événements : un seul outil de validation) ; **OpenAPI et documentation `/docs` générées automatiquement** (utile pour la passerelle au TD2 et les tests de contrat au TD5) ; *lifespan* pour démarrer et arrêter proprement les clients Kafka ; `TestClient` pour tester sans serveur ; asynchrone natif ; très répandu.
- Inconvénients : moins « tout compris » que Django (l'ORM et les migrations seront à choisir au TD2, par ADR) ; il faut comprendre la frontière entre code async et appels bloquants.

## Décision

**FastAPI + uvicorn**, avec **Pydantic v2** et **pydantic-settings** pour la configuration.

Conventions des services :
- `create_app(...)` : fabrique d'application, dépendances injectables pour les tests ;
- `lifespan` : création et fermeture des clients Kafka ;
- `__main__.py` : `python -m <service> [--reload]` lit le port dans `.env` et lance uvicorn, qui gère SIGINT et SIGTERM ;
- appels bloquants (Kafka) exécutés via `asyncio.to_thread`.

## Conséquences

- **Positives** : services courts et lisibles ; un seul langage de validation (Pydantic) pour les API et les événements ; documentation d'API gratuite.
- **Négatives** : écart avec le cahier des charges initial, d'où des documents à tenir cohérents (vision, AGENTS.md, README) ; le choix de l'accès aux bases (SQLAlchemy, SQLModel, psycopg seul…) reste à faire au TD2, par ADR.
- **Impact** : `packages/contracts` et `packages/kafka` sont des paquets Python ; le smoke test reste en Node, sans dépendance ; l'interface Next.js (TD2) ne voit que des API REST et n'est pas concernée.
