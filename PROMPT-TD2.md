# Prompt TD2 — Catalogue, passerelle d'API et interface Next.js

> **Brouillon à valider par l'enseignant.** Les choix marqués 🔶 sont des propositions : les modifier ici avant de lancer le TD.

Le contexte permanent du projet (vision, rôles, architecture cible, exigences non fonctionnelles, feuille de route) est dans [`docs/vision.md`](docs/vision.md) et [`AGENTS.md`](AGENTS.md). **Lis-les d'abord**, ainsi que les ADR existants ([`docs/adr/`](docs/adr/)) et la documentation d'architecture ([`docs/architecture/`](docs/architecture/README.md)).

---

## Décisions structurantes à valider 🔶

Chacune fera l'objet d'un ADR (règle d'AGENTS.md : pas de nouveau framework ou pattern sans ADR).

| # | Sujet | Proposition | Alternatives écartées (à justifier dans l'ADR) |
| --- | --- | --- | --- |
| ADR 0006 | Accès aux données | **SQLAlchemy 2** (style typé `Mapped[...]`, sessions synchrones) + **psycopg 3** + **Alembic** pour les migrations | SQLModel, ORM de Django, SQL brut avec psycopg seul, SQLAlchemy async |
| ADR 0007 | Passerelle d'API | **Service FastAPI** (`services/gateway`) qui fait proxy vers les services, avec une liste blanche de routes | Traefik, Kong, NGINX, appels directs de l'interface vers les services |
| ADR 0008 | Recherche | **Recherche plein texte PostgreSQL** (`tsvector` généré, dictionnaire `french`, index GIN) | `ILIKE`, Meilisearch, Elasticsearch/OpenSearch |
| ADR 0009 | Interface | **Next.js 16 App Router**, rendu côté serveur (Server Components), **CSS Modules** (aucune bibliothèque d'interface) | Tailwind, bibliothèques de composants, rendu côté client (SPA) |

---

# Tâche actuelle : TD2 uniquement

Point de départ : le tag `td1` (socle fonctionnel : Kafka, PostgreSQL, catalog / identity / stats squelettes, `system.ping`).

**Ne code que le TD2.** N'anticipe pas l'envoi de vidéos (TD3), la lecture (TD4) ni l'authentification (TD5). Choisis en revanche des structures qui les accueilleront sans refonte.

## Objectif

Un visiteur ouvre `http://localhost:3000`, parcourt les chaînes et les vidéos du catalogue, fait une recherche (« javascript ») et consulte une fiche vidéo. Les données viennent de la **base du service catalog**, et passent par la **passerelle d'API**, que l'interface est la seule à appeler.

```
Navigateur ──▶ apps/web (Next.js :3000) ──▶ services/gateway (:4000) ──▶ services/catalog (:3001) ──▶ PostgreSQL (base catalog)
```

## 1. Service catalog avec sa base

### Modèle de données (base `catalog`, utilisateur `catalog`)

- **`channels`** : `id` (UUID), `handle` (unique, format `[a-z0-9-]{3,30}`, utilisé dans les URL), `name`, `description`, `created_at`.
- **`videos`** : `id` (UUID), `channel_id` (FK vers `channels`), `title`, `description`, `duration_seconds` (> 0), `published_at`, `created_at`, plus la colonne de recherche `search_vector` (`tsvector` **généré** à partir du titre, pondéré A, et de la description, pondérée B) avec un **index GIN**.
- **Pas de colonne de statut de transcodage ni d'URL de média** : elles arriveront au TD3 **par une nouvelle migration Alembic**. C'est l'occasion de montrer comment on fait évoluer un schéma.
- Recherche insensible aux accents : extension `unaccent` (extension « trusted » depuis PostgreSQL 13 ; à vérifier : sinon la créer dans le script d'init de PostgreSQL avec le super-utilisateur).

### Migrations et données de démonstration

- Alembic dans `services/catalog/migrations/`, première migration qui crée le schéma. Commande racine **`pnpm db:migrate`** (`alembic upgrade head` sur la base catalog).
- **`pnpm db:seed`** : insère des données **fictives** (aucune donnée réelle) : environ 5 chaînes et 30 vidéos sur des thèmes de cours (JavaScript, Python, réseaux, bases de données, Kafka…). Le script est **idempotent** (relancer ne crée pas de doublons).

### API REST (lecture seule au TD2)

| Méthode | Route | Rôle |
| --- | --- | --- |
| `GET` | `/channels` | Liste des chaînes |
| `GET` | `/channels/{handle}` | Une chaîne et ses vidéos récentes (404 si inconnue) |
| `GET` | `/videos?q=&channel=&limit=&offset=` | Liste paginée ; `q` = recherche plein texte classée par pertinence (`ts_rank`), sinon tri par `published_at` décroissant ; `limit` 20 par défaut, 50 maximum |
| `GET` | `/videos/{id}` | Fiche vidéo avec sa chaîne (404 si inconnue) |

- Réponses JSON en **camelCase** (même convention que l'enveloppe d'événement), schémas Pydantic distincts des modèles SQLAlchemy.
- Réponse paginée : `{ items, total, limit, offset }`.
- `GET /health` vérifie aussi la connexion à la base (`SELECT 1`) et répond 503 si elle échoue.
- `POST /dev/ping` reste inchangé.
- Configuration : `CATALOG_DATABASE_URL` (dans `.env.example`, avec l'utilisateur `catalog` et non le super-utilisateur).

### Tests

- Tests unitaires sans base (schémas, validation des paramètres).
- **Tests d'intégration sur un vrai PostgreSQL** (requêtes, recherche, pagination) dans une base de test dédiée, marqués `@pytest.mark.db`. En local, ils utilisent le PostgreSQL de Docker Compose ; en CI, un conteneur `services: postgres` de GitHub Actions. En CI, ils ne doivent **jamais** être ignorés.

## 2. Passerelle d'API (`services/gateway`, port 4000)

- Service FastAPI qui **relaie** les requêtes : `GET /api/catalog/...` → `http://localhost:3001/...` (client HTTP asynchrone `httpx2`, déjà présent dans le dépôt).
- **Liste blanche de routes** : seules les routes publiques sont exposées. `POST /dev/ping` et `/docs` des services **ne passent pas** par la passerelle.
- Ajoute un en-tête **`X-Request-Id`** (généré s'il est absent) transmis au service et renvoyé au client, et journalise chaque requête (méthode, chemin, statut, durée, request id).
- **Délais d'attente** : service injoignable → `502`, trop lent → `504`, avec un corps d'erreur JSON uniforme `{ error, requestId }`.
- **CORS** limité à l'origine de l'interface (`http://localhost:3000`).
- `GET /health` : santé de la passerelle ; `GET /health/services` : santé de chaque service en aval.
- Hors périmètre (TD5) : vérification des JWT, limitation de débit. Prévoir l'emplacement (middleware) sans l'implémenter.
- Tests : avec de faux services en aval (transport `httpx2` simulé), sans démarrer catalog.

## 3. Interface Next.js 16 (`apps/web`, port 3000)

- Next.js 16, App Router, TypeScript strict, **Server Components** : les pages appellent la passerelle **côté serveur** (`GATEWAY_URL`), le navigateur reçoit du HTML. C'est économe en données et il n'y a pas d'appel croisé navigateur → API à sécuriser au TD2.
- Pages :
  - `/` : dernières vidéos ;
  - `/search?q=` : résultats de recherche (formulaire `GET`, fonctionne sans JavaScript) ;
  - `/channels/[handle]` : page de chaîne ;
  - `/videos/[id]` : fiche vidéo (titre, chaîne, durée, date, description ; **emplacement** réservé au lecteur, qui viendra au TD4).
- États gérés : chargement (`loading.tsx`), page introuvable (`not-found.tsx`), passerelle indisponible (`error.tsx` avec message clair).
- **CSS Modules** uniquement, sans bibliothèque d'interface ; vignettes générées en CSS ou SVG à partir du titre (**aucune image téléchargée**) ; mise en page responsive et accessible (contrastes, navigation au clavier, `lang="fr"`).
- Petit client typé `lib/gateway.ts` (types des réponses du catalogue), testé avec **Vitest** (formatage de durée, construction des URL…).
- Scripts du projet : `dev`, `build`, `typecheck` (`tsc --noEmit`), `lint`, `test` (orchestrés par turbo comme les projets Python).

## 4. Intégration, smoke test et CI

- `pnpm dev` lance aussi `gateway` et `web`. Ordre conseillé dans le README : `infra:up`, `db:migrate`, `db:seed`, `dev`.
- `pnpm smoke` est étendu : santé de la passerelle et de `/health/services` ; `GET /api/catalog/videos?q=...` via la passerelle renvoie au moins un résultat seedé ; la page `/` de l'interface répond 200 et contient un titre seedé ; `POST /dev/ping` **n'est pas** accessible via la passerelle (404). Le scénario ping du TD1 reste vérifié.
- CI : ajouter un conteneur PostgreSQL de service pour les tests `db`, appliquer les migrations, et vérifier `typecheck`, `lint` et `test` de `apps/web` (plus `next build`).

## 5. Documentation et gouvernance à mettre à jour

- **ADR 0006 à 0009** (voir le tableau en tête).
- `docs/architecture/02-conteneurs.md` : diagramme « état au TD2 ».
- `docs/architecture/06-donnees.md` : schéma de la base catalog (diagramme entité-association Mermaid), migrations.
- Nouveau `docs/architecture/07-passerelle.md` : routage, liste blanche, request id, erreurs, ce qui viendra au TD5.
- Nouveau `docs/architecture/08-interface.md` : pages, stratégie de rendu, appel à la passerelle.
- `AGENTS.md` (structure, commandes, ports, étape en cours = TD2), `README.md` (démarrage complet, dépannage base et migrations), `.env.example`.

## Économie de données

- Avant tout téléchargement, liste ce qui manque et sa taille approximative, et **attends mon accord** : paquets npm de Next.js (environ 200 à 300 Mo estimés), paquets Python (SQLAlchemy, psycopg, Alembic : quelques dizaines de Mo).
- **Aucune nouvelle image Docker** n'est nécessaire (PostgreSQL déjà présent).
- `pnpm install --prefer-offline` ; versions épinglées, jamais de `latest`.
- Pas de polices ni d'images distantes dans l'interface (pas de Google Fonts : polices système).

## Façon de travailler

1. Lis ce document, la vision, AGENTS.md, les ADR et l'architecture ; présente le plan et la liste des fichiers. **Attends ma validation.**
2. Travaille sur une **branche** (`td2`) et avance par étapes, avec un commit à chaque étape qui fonctionne ; ouvre une **PR** vers `main` à la fin.
3. **Protocole pédagogique** (comme au TD1) : avant chaque étape, une leçon (concept, pourquoi, comment on l'implémente, comment tu vas le faire, pièges) ; pendant, des explications ; après, un « À retenir ».
4. Vérifie chaque nouvelle dépendance (existence, maintenance, licence) avant de l'ajouter.
5. À la fin, lance toi-même : `pnpm install`, `pnpm typecheck`, `pnpm lint`, `pnpm test`, `pnpm infra:up`, `pnpm db:migrate`, `pnpm db:seed`, `pnpm dev`, `pnpm smoke`. Corrige jusqu'à ce que tout passe.
6. Termine par un résumé (ce qui a été créé, commandes) et **5 questions** pour les étudiants (migrations, recherche plein texte et index GIN, rôle de la passerelle et liste blanche, rendu côté serveur, une base par service).

## Critères d'acceptation du TD2

- [ ] `pnpm db:migrate` crée le schéma dans la base `catalog` avec l'utilisateur `catalog` ; `pnpm db:seed` est idempotent.
- [ ] `GET /videos?q=kafka` (via la passerelle : `/api/catalog/videos?q=kafka`) renvoie les vidéos pertinentes, classées ; la recherche ignore les accents (« reseau » trouve « réseau »).
- [ ] La passerelle expose uniquement les routes de la liste blanche (`/dev/ping` renvoie 404 via la passerelle), ajoute `X-Request-Id` et renvoie 502/504 avec un JSON uniforme si catalog est arrêté ou lent.
- [ ] `http://localhost:3000` affiche les dernières vidéos ; recherche, page de chaîne et fiche vidéo fonctionnent, y compris JavaScript désactivé ; les erreurs (404, passerelle arrêtée) sont gérées proprement.
- [ ] L'interface n'appelle **que** la passerelle (aucune URL de service dans `apps/web`).
- [ ] `pnpm typecheck`, `pnpm lint`, `pnpm test` et `pnpm smoke` passent ; la CI exécute les tests d'intégration sur PostgreSQL et le `next build`.
- [ ] ADR 0006 à 0009, documentation d'architecture, AGENTS.md et README sont à jour.
