# Guide de lecture — rattraper un TD de StreamLab

> **Pour qui ?** Les étudiants qui ont manqué une séance de TD, ou qui veulent revoir le projet à leur rythme.
> **Comment ?** En lisant les fichiers **dans l'ordre proposé**, en faisant les **expériences**, puis en répondant aux **questions d'auto-évaluation**.
> **Durée estimée pour le TD1 :** 2 h à 3 h (lecture 1 h 30, expériences 1 h).

Ce guide ne remplace pas le code : il vous dit **quoi ouvrir, dans quel ordre, et quoi y remarquer**. Gardez votre éditeur ouvert à côté.

## Sommaire

1. [Le projet en 5 minutes](#1-le-projet-en-5-minutes)
2. [Récupérer le projet dans l'état d'un TD](#2-récupérer-le-projet-dans-létat-dun-td)
3. [TD1 — parcours de lecture](#3-td1--parcours-de-lecture)
4. [TD1 — expériences à faire soi-même](#4-td1--expériences-à-faire-soi-même)
5. [TD1 — auto-évaluation](#5-td1--auto-évaluation)
6. [Glossaire](#6-glossaire)
7. [Méthode pour lire un projet que l'on ne connaît pas](#7-méthode-pour-lire-un-projet-que-lon-ne-connaît-pas)

---

## 1. Le projet en 5 minutes

**StreamLab** est une plateforme de streaming vidéo éducative (un YouTube ou un Twitch simplifié), construite par **toute la promotion** : six TD construisent un socle, puis chaque groupe ajoute un module (chat, direct, abonnements…) dans le même dépôt.

L'architecture repose sur trois idées :

| Idée | En une phrase | Où la voir |
| --- | --- | --- |
| **Microservices** | L'application est découpée en petits services indépendants (catalog, identity, stats…), chacun avec **sa propre base de données**. | `services/` |
| **Événements Kafka** | Les services ne s'appellent pas directement : l'un **publie un événement** (« une vidéo a été envoyée »), les autres s'y **abonnent**. | `packages/kafka`, `docker-compose.yml` |
| **Contrats partagés** | La forme des événements est définie **une seule fois**, dans un paquet importé par tous. | `packages/contracts` |

La pile technique : **Python + FastAPI** pour les services, **Kafka 4** pour les événements, **PostgreSQL** pour les données, **Docker** pour l'infrastructure, **pnpm + Turborepo + uv** pour organiser le dépôt.

👉 Pour la vision complète : [`docs/vision.md`](vision.md).

## 2. Récupérer le projet dans l'état d'un TD

Chaque TD terminé est marqué par un **tag Git** (`td1`, `td2`…). Un tag est une étiquette posée sur un commit : il permet de revenir exactement à l'état du projet à la fin d'une séance.

```powershell
# 1. Forker le dépôt sur GitHub (bouton « Fork »), puis cloner VOTRE fork
git clone https://github.com/<votre-compte>/streamlab.git
cd streamlab

# 2. Se placer sur l'état de la fin du TD1, dans une branche à vous
git switch -c rattrapage-td1 td1

# 3. Installer et lancer : suivre le README, section « Démarrage pas à pas »
```

Le [README](../README.md) décrit l'installation sous Windows (prérequis, commandes, dépannage). **Faites-le fonctionner avant de lire le code** : lire du code que l'on peut exécuter est beaucoup plus facile.

✅ Vous êtes prêt quand `pnpm smoke` affiche `✅ Smoke test réussi`.

---

## 3. TD1 — parcours de lecture

**Objectif du TD1 :** poser le socle et prouver qu'un événement **traverse Kafka** d'un service à un autre : `catalog` publie un `system.ping`, `stats` le reçoit.

```
POST /dev/ping ─▶ catalog ─▶ Kafka (topic system.ping, 3 partitions) ─▶ stats ─▶ GET /stats/pings
```

Lisez les étapes dans l'ordre. Chacune indique les fichiers, **ce qu'il faut remarquer** et la notion à retenir.

### Étape 1 — Le cadre (15 min)

| Fichier | Ce qu'il faut remarquer |
| --- | --- |
| [`AGENTS.md`](../AGENTS.md) | Les **règles du dépôt** : conventions (noms de topics, enveloppe d'événement, une base par service) et règles de travail (branche + PR, tests d'abord, ADR). C'est la « constitution » du projet. |
| [`docs/architecture/01-contexte.md`](architecture/01-contexte.md) puis [`02-conteneurs.md`](architecture/02-conteneurs.md) | Deux niveaux de zoom (modèle **C4**) : qui utilise le système, puis de quelles applications il est fait. Comparez le diagramme « cible » et le diagramme « état au TD1 ». |
| [`docs/adr/0001-microservices-et-kafka.md`](adr/0001-microservices-et-kafka.md) | Un **ADR** (Architecture Decision Record) : pourquoi des microservices et Kafka plutôt qu'un monolithe. Lisez surtout « Options envisagées » : une décision se justifie par les alternatives écartées. |

💡 **À retenir :** on documente **pourquoi** on a choisi, pas seulement **quoi**.

### Étape 2 — L'organisation du dépôt (15 min)

| Fichier | Ce qu'il faut remarquer |
| --- | --- |
| [`package.json`](../package.json) (racine) | Les **scripts** que vous lancez (`pnpm dev`, `pnpm test`, `pnpm infra:up`…). La plupart délèguent à `turbo` ou à `docker compose`. |
| [`pnpm-workspace.yaml`](../pnpm-workspace.yaml) et [`turbo.json`](../turbo.json) | Le **monorepo** : un seul dépôt, plusieurs projets (`apps/*`, `packages/*`, `services/*`). Turborepo lance la même tâche dans chaque projet. |
| [`pyproject.toml`](../pyproject.toml) (racine) | Le **workspace uv** côté Python : la liste des projets Python et la configuration commune de ruff, mypy et pytest. |
| [`services/stats/package.json`](../services/stats/package.json) | L'astuce du dépôt : un projet Python a un petit `package.json` dont les scripts appellent `uv run …`. C'est ce qui permet à turbo de l'orchestrer. |

💡 **À retenir :** deux gestionnaires de paquets (uv pour Python, pnpm pour JavaScript), un seul chef d'orchestre (turbo). Détails : [ADR 0002](adr/0002-monorepo-polyglotte-pnpm-turborepo-uv.md).

### Étape 3 — L'infrastructure Docker (20 min)

| Fichier | Ce qu'il faut remarquer |
| --- | --- |
| [`docker-compose.yml`](../docker-compose.yml) | Quatre conteneurs : `kafka`, `kafka-init`, `kafka-ui`, `postgres`. Lisez les commentaires de `kafka`, en particulier les **trois listeners** et `KAFKA_AUTO_CREATE_TOPICS_ENABLE: "false"`. |
| [`infra/kafka/create-topics.sh`](../infra/kafka/create-topics.sh) | Création du topic `system.ping` avec **3 partitions**. `--if-not-exists` rend le script rejouable. |
| [`infra/postgres/init/`](../infra/postgres/init/) | Une base et un utilisateur **par service** ; `REVOKE ... FROM PUBLIC` empêche un service de se connecter à la base d'un autre. |
| [`docs/architecture/04-infrastructure-locale.md`](architecture/04-infrastructure-locale.md) | L'explication des listeners : **le point le plus important, et le plus souvent mal compris**. |

💡 **À retenir :** le broker Kafka a deux adresses. `localhost:9092` est pour les programmes lancés sur votre PC, `kafka:19092` pour les autres conteneurs : dans un conteneur, `localhost` désigne le conteneur lui-même.

### Étape 4 — Le contrat d'événement (20 min)

Ouvrez [`packages/contracts/src/streamlab_contracts/`](../packages/contracts/src/streamlab_contracts/) :

1. **`topics.py`** : les noms de topics, déclarés une seule fois. Convention `<domaine>.<événement au passé>`.
2. **`envelope.py`** : le cœur du TD1.
   - `EventEnvelope` : les champs communs à **tous** les événements (`eventId`, `type`, `version`, `occurredAt`, `source`, `payload`).
   - `create_event` : fabrique un événement (UUID, date UTC).
   - `parse_event` : valide un message reçu **en deux temps**, d'abord l'enveloppe, puis le payload selon `(type, version)`.
   - Le `model_config` : `to_camel` (`event_id` en Python devient `eventId` en JSON), `frozen` (un événement ne se modifie pas), `extra="forbid"` (un champ inconnu est une erreur).
3. **`events/system_ping.py`** : le payload du ping et son enregistrement dans le registre.

Lisez ensuite les tests [`packages/contracts/tests/test_envelope.py`](../packages/contracts/tests/test_envelope.py). Leurs noms se lisent comme une **spécification** (`test_rejette_un_type_inconnu`…).

💡 **À retenir :** `eventId` sert à détecter les doublons et `version` à faire évoluer un événement sans casser ceux qui le lisent. Détails : [ADR 0004](adr/0004-enveloppe-evenement-commune.md) et [catalogue des événements](architecture/05-evenements.md).

### Étape 5 — Publier et consommer (25 min)

Ouvrez [`packages/kafka/src/streamlab_kafka/`](../packages/kafka/src/streamlab_kafka/) :

1. **`publisher.py`**
   - `create_publisher` : `enable.idempotence=True`, c'est-à-dire que Kafka élimine les doublons dus aux renvois réseau.
   - `publish` : la **clé** du message choisit la partition. La méthode attend l'accusé de Kafka (`flush`) pour renvoyer la partition et l'offset.
2. **`consumer.py`** : lisez dans cet ordre.
   - Le docstring du module, avec les trois principes.
   - `process_message` : un message invalide est **journalisé puis ignoré**. Pourquoi ? Sinon il serait relu en boucle et bloquerait la partition.
   - `RunningConsumer._run` : la boucle `poll` → traitement → **commit**. Le commit vient **après** le traitement.
   - `start_consumer` : `group.id`, `auto.offset.reset=earliest`, `enable.auto.commit=False`.

💡 **À retenir :** commiter après le traitement signifie qu'en cas de panne, un message peut être relu (livraison « **au moins une fois** »). Le consommateur doit donc être **idempotent**.

### Étape 6 — Les trois services (25 min)

| Fichier | Ce qu'il faut remarquer |
| --- | --- |
| [`services/identity/src/identity_service/main.py`](../services/identity/src/identity_service/main.py) | Le **modèle commun** à tous les services : `create_app()` (fabrique), `lifespan` (démarrage avant `yield`, arrêt propre après), route `/health`. Commencez par lui, c'est le plus court. |
| [`services/catalog/src/catalog_service/main.py`](../services/catalog/src/catalog_service/main.py) | `POST /dev/ping` : `create_event`, puis `publish` exécuté avec `asyncio.to_thread` (un appel bloquant ne doit pas geler un serveur async). Le publisher est **injecté** dans `create_app` : les tests passent un faux publisher. |
| [`services/stats/src/stats_service/ping_store.py`](../services/stats/src/stats_service/ping_store.py) | L'**idempotence** concrète : un ensemble des `eventId` déjà vus. Le **verrou** (`threading.Lock`) est là parce que le thread Kafka écrit pendant que les requêtes HTTP lisent. |
| [`services/stats/src/stats_service/main.py`](../services/stats/src/stats_service/main.py) | Le consommateur démarré dans le `lifespan` et arrêté proprement (`consumer.stop()`). |
| `services/*/src/*/__main__.py` | `python -m catalog_service` : lit le port dans `.env` et lance uvicorn. |

Lisez ensuite un fichier de test, par exemple [`services/catalog/tests/test_routes.py`](../services/catalog/tests/test_routes.py), et repérez le `FakePublisher`.

💡 **À retenir :** fabrique + injection de dépendances permettent de tester sans Kafka. Un arrêt propre (`close()`) fait **quitter le groupe** immédiatement ; un arrêt brutal laisse un « membre fantôme ».

### Étape 7 — Vérifier le tout (10 min)

| Fichier | Ce qu'il faut remarquer |
| --- | --- |
| [`scripts/smoke-test.mjs`](../scripts/smoke-test.mjs) | Le test de **bout en bout** : santé des services, publication, réception en moins de 10 s. |
| [`.github/workflows/ci.yml`](../.github/workflows/ci.yml) | La **CI** : à chaque push, une machine vierge installe tout et lance typecheck, lint et tests, sur Python 3.12 et 3.14. |
| [`docs/architecture/03-flux-ping-td1.md`](architecture/03-flux-ping-td1.md) | Le diagramme de séquence qui récapitule tout le trajet du ping. **Si vous ne lisez qu'un document, lisez celui-là.** |

---

## 4. TD1 — expériences à faire soi-même

Prérequis : `pnpm infra:up`, puis `pnpm dev` dans un terminal. Les commandes ci-dessous sont pour PowerShell.

### Expérience 1 — Clé et partition

```powershell
# Sans clé : la clé est l'eventId, les pings se répartissent
1..6 | ForEach-Object { curl.exe -s -X POST localhost:3001/dev/ping; "" }

# Avec la même clé : toujours la même partition
1..6 | ForEach-Object { curl.exe -s -X POST localhost:3001/dev/ping -H "content-type: application/json" -d '{\"key\":\"abc\"}'; "" }
```

❓ Que constatez-vous sur le champ `partition` ? Et sur `offset` d'un appel à l'autre ?

### Expérience 2 — Stats rattrape son retard

1. Arrêtez tout avec Ctrl+C, puis relancez **seulement** catalog : `cd services/catalog; uv run python -m catalog_service`.
2. Publiez 3 pings (voir l'expérience 1).
3. Dans un autre terminal, relancez stats : `cd services/stats; uv run python -m stats_service`.
4. `curl.exe localhost:3003/stats/pings`.

❓ Combien de pings stats a-t-il reçus ? Pourquoi pas ceux des expériences précédentes ? (Indice : regardez la page du groupe `stats-service` dans Kafbat UI, http://localhost:8080.)

### Expérience 3 — Un message invalide ne bloque rien

1. Dans Kafbat UI : *Topics → system.ping → Produce Message*. Valeur : `bonjour` (ce n'est pas du JSON). Envoyez.
2. Regardez les journaux de stats : une ligne `Message invalide ignoré ... partition=... offset=...`.
3. Publiez ensuite un vrai ping : il est bien reçu.

❓ Que se passerait-il si `process_message` levait une exception au lieu de journaliser ?

### Expérience 4 — Deux instances de stats se partagent les partitions

```powershell
# Terminal A (stats sur le port 3003)
cd services/stats; uv run python -m stats_service
# Terminal B (une deuxième instance, même groupe, autre port)
cd services/stats; $env:STATS_PORT=3004; uv run python -m stats_service
```

Publiez une dizaine de pings sans clé, puis comparez `curl.exe localhost:3003/stats/pings` et `curl.exe localhost:3004/stats/pings`.

❓ Les deux instances ont-elles reçu les mêmes pings ? Dans Kafbat UI, quelles partitions sont attribuées à chacune ? Que se passerait-il avec 4 instances ?

### Expérience 5 — Casser un test, volontairement

Dans [`packages/contracts/src/streamlab_contracts/events/system_ping.py`](../packages/contracts/src/streamlab_contracts/events/system_ping.py), passez `min_length=1` à `min_length=0`, puis lancez `cd packages/contracts; uv run pytest`. Remettez la valeur d'origine.

❓ Quel test échoue, et que protège-t-il ?

---

## 5. TD1 — auto-évaluation

Répondez **avant** d'ouvrir les réponses.

<details>
<summary><b>1. Pourquoi le topic system.ping a-t-il 3 partitions, et qu'est-ce qui décide de la partition d'un message ?</b></summary>

Les partitions permettent de **paralléliser** : jusqu'à 3 instances d'un même service peuvent lire en même temps, une partition chacune. La **clé** du message décide de la partition (`hash(clé) % 3`) : même clé, même partition. L'ordre n'est garanti **qu'à l'intérieur d'une partition** : pour garder l'ordre des événements d'une même vidéo, on prendra `videoId` comme clé.
</details>

<details>
<summary><b>2. Qu'est-ce qu'un groupe de consommateurs ? Que reçoit un nouveau service qui s'abonne avec son propre groupe ?</b></summary>

Les instances d'un même service partagent un `group.id` : Kafka **répartit les partitions** entre elles, et chaque message est traité **une fois par groupe**. Un autre service, avec un autre groupe, reçoit **tous** les messages de son côté. Chaque groupe a ses propres offsets : c'est le modèle publication/abonnement.
</details>

<details>
<summary><b>3. Le producteur est idempotent. Pourquoi le consommateur doit-il l'être aussi ?</b></summary>

L'idempotence du producteur élimine les doublons dus aux **renvois réseau** entre producteur et broker. Mais le consommateur commite **après** traitement : s'il plante entre le traitement et le commit, il **relit** le message au redémarrage. C'est la livraison « au moins une fois ». Il doit donc reconnaître un `eventId` déjà traité et l'ignorer.
</details>

<details>
<summary><b>4. Pourquoi stats n'a-t-il pas le droit de lire directement la base de catalog ?</b></summary>

Règle « **une base par service** » : chaque service est propriétaire de ses données et peut changer son schéma sans prévenir les autres. Lire la base d'un autre crée un **couplage caché** : un renommage de colonne casserait stats sans que catalog le sache. On passe par l'**API** ou par les **événements**, qui sont des contrats versionnés. La base le garantit techniquement : l'utilisateur `stats` n'a pas le droit `CONNECT` sur la base `catalog`.
</details>

<details>
<summary><b>5. Pourquoi Kafbat UI utilise-t-il kafka:19092 alors que les services Python utilisent localhost:9092 ?</b></summary>

Après la connexion initiale, le broker renvoie au client **l'adresse à utiliser** (advertised listener). Depuis le PC, le broker est sur `localhost:9092` (port publié par Docker). Depuis un conteneur, `localhost` désigne **le conteneur lui-même**. Il faut donc le nom DNS `kafka` et le listener interne `19092`. Avec un seul listener annoncé comme `localhost:9092`, Kafbat UI se connecterait puis échouerait.
</details>

<details>
<summary><b>6. Pourquoi un message invalide est-il journalisé puis ignoré, au lieu de faire planter le consommateur ?</b></summary>

S'il plantait, le message ne serait jamais commité : au redémarrage, le consommateur le relirait et replanterait, **indéfiniment** (« poison pill »). La partition serait bloquée et plus aucun message valide derrière lui ne serait traité. Au TD6, on l'enverra dans une **DLQ** (file des messages en erreur) au lieu de simplement l'ignorer.
</details>

<details>
<summary><b>7. Pourquoi POST /dev/ping renvoie-t-il 202 et non 200 ?</b></summary>

**202 Accepted** signifie « reçu, le traitement aura lieu plus tard ». L'événement est bien dans Kafka, mais catalog ne sait pas qui le lira, ni quand. Le traitement par stats est **asynchrone**.
</details>

<details>
<summary><b>8. À quoi sert le lifespan d'une application FastAPI ?</b></summary>

C'est le code qui encadre la vie du serveur. **Avant `yield`** : démarrage (créer le producteur, démarrer le consommateur). **Après `yield`** : arrêt propre, déclenché par Ctrl+C ou SIGTERM via uvicorn (envoyer les messages en attente, fermer le consommateur pour qu'il quitte son groupe).
</details>

---

## 6. Glossaire

| Terme | Définition courte |
| --- | --- |
| **ADR** | *Architecture Decision Record* : une page par décision importante (contexte, options, décision, conséquences). Dossier `docs/adr/`. |
| **Broker** | Serveur Kafka qui stocke les messages et les sert aux clients. |
| **Clé (de message)** | Valeur jointe à un message Kafka ; elle détermine sa partition. |
| **Commit (d'offset)** | Enregistrer dans Kafka jusqu'où un groupe a lu une partition. |
| **Consommateur / groupe** | Programme qui lit un topic. Les consommateurs d'un même groupe se partagent les partitions. |
| **Contrat** | Forme convenue d'un message ou d'une API, partagée entre producteur et consommateur. |
| **Enveloppe** | Champs communs à tous les événements StreamLab (`eventId`, `type`, `version`, `occurredAt`, `source`, `payload`). |
| **Idempotent** | Qu'on peut exécuter plusieurs fois avec le même résultat qu'une seule. |
| **KRaft** | Mode de Kafka sans ZooKeeper : Kafka gère lui-même ses métadonnées (protocole Raft). |
| **Lifespan** | Démarrage et arrêt d'une application FastAPI. |
| **Listener (advertised)** | Adresse sur laquelle Kafka écoute, et celle qu'il **annonce** aux clients. |
| **Monorepo** | Un seul dépôt Git pour plusieurs applications et bibliothèques. |
| **Offset** | Position d'un message dans une partition (0, 1, 2…). |
| **Partition** | Sous-division ordonnée d'un topic. |
| **Payload** | Contenu métier d'un événement, propre à chaque type. |
| **Poison pill** | Message invalide qui bloque une partition si le consommateur plante dessus. |
| **Smoke test** | Test rapide de bout en bout qui vérifie le chemin principal. |
| **Topic** | Journal d'événements nommé (`system.ping`). |

---

## 7. Méthode pour lire un projet que l'on ne connaît pas

Cette méthode vaut pour StreamLab comme pour tout projet en entreprise :

1. **Faire tourner avant de lire.** Un projet qui fonctionne sur sa machine se lit deux fois plus vite.
2. **Lire la documentation du haut vers le bas** : vision, puis architecture, puis décisions (ADR), puis code.
3. **Suivre un flux de bout en bout**, plutôt que lire les fichiers par ordre alphabétique. Ici : `POST /dev/ping` → … → `GET /stats/pings`.
4. **Lire les tests** : ils disent ce que le code est **censé** faire, avec des exemples.
5. **Modifier pour comprendre** : changer une valeur, relancer, observer ce qui casse (et revenir en arrière avec `git restore .`).
6. **Noter ses questions** et les apporter en séance, ou les poser dans une issue GitHub du dépôt du cours.

---

> **TD suivants :** une section sera ajoutée à ce guide à la fin de chaque TD (parcours, expériences, auto-évaluation).
