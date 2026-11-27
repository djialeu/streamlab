# StreamLab

Plateforme de **streaming vidéo éducative** (YouTube et Twitch simplifiés) : projet fil rouge du cours « Technologie web et applications » (M2 Génie logiciel).

> **Étape actuelle : TD1, le socle.** Monorepo, infrastructure Docker (Kafka 4 KRaft, Kafbat UI, PostgreSQL), trois services FastAPI squelettes, et un événement `system.ping` qui traverse Kafka de `catalog` à `stats`.

- Vision et feuille de route : [`docs/vision.md`](docs/vision.md)
- Architecture (C4, flux, événements, données) : [`docs/architecture/`](docs/architecture/README.md)
- Décisions (ADR) : [`docs/adr/`](docs/adr/)
- Règles pour les agents de code et les contributeurs : [`AGENTS.md`](AGENTS.md)

---

## 1. Prérequis (Windows)

| Outil | Version | Vérifier | Installer |
| --- | --- | --- | --- |
| Docker Desktop (backend WSL 2) | récent | `docker version` | https://docs.docker.com/desktop/ |
| Node.js | ≥ 24 (`.nvmrc`) | `node -v` | https://nodejs.org (LTS) |
| pnpm | 12.23.0 (fixé par `packageManager`) | `pnpm -v` | via **corepack**, voir ci-dessous |
| Python | ≥ 3.12 | `python --version` | https://www.python.org |
| uv | ≥ 0.13 | `uv --version` | voir ci-dessous |
| Git | récent | `git --version` | https://git-scm.com |

### Activer pnpm avec corepack

Corepack est fourni avec Node. Il installe **exactement** la version de pnpm indiquée dans `package.json`, la même pour toute la promotion.

```powershell
corepack enable
```

> **Erreur `EPERM: operation not permitted, open 'C:\Program Files\nodejs\pnpm'`** : Node est installé dans un dossier protégé. Deux solutions : relancer le terminal **en administrateur**, ou installer le raccourci dans un dossier utilisateur déjà présent dans le PATH :
> ```powershell
> corepack enable --install-directory "$env:APPDATA\npm" pnpm
> ```

### Installer uv

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
# ou, si Python est déjà installé :
python -m pip install --user uv
```

> Avec `pip install --user`, `uv.exe` arrive dans `%APPDATA%\Python\Python3XX\Scripts`, qui n'est pas toujours dans le PATH. Ajoutez ce dossier au PATH, ou copiez `uv.exe` dans `%USERPROFILE%\.local\bin`.

### Limiter la mémoire de WSL 2 (recommandé sur 8 Go)

Par défaut, WSL 2 peut prendre jusqu'à la moitié de la RAM. Créez `%USERPROFILE%\.wslconfig` :

```ini
[wsl2]
memory=4GB      # 4 Go sur une machine de 8 Go, 6 Go sur 16 Go
processors=4
swap=2GB
```

Puis appliquez : `wsl --shutdown` et redémarrez Docker Desktop. L'infrastructure du TD1 consomme environ **750 Mo** au repos.

---

## 2. Démarrage pas à pas

```powershell
# 1. Cloner puis se placer dans le dépôt
git clone <url-du-depot> streamlab
cd streamlab

# 2. Configuration locale (ports, mots de passe de dev)
Copy-Item .env.example .env

# 3. Dépendances (le cache local est réutilisé : économe en données)
pnpm install --prefer-offline   # turbo
pnpm setup                      # uv sync --all-packages : crée .venv avec tous les projets Python

# 4. Infrastructure : Kafka, kafka-init, Kafbat UI, PostgreSQL
pnpm infra:up
docker compose ps -a            # kafka et postgres « healthy », kafka-init « Exited (0) »

# 5. Les trois services (laisser ce terminal ouvert ; Ctrl+C pour arrêter)
pnpm dev

# 6. Dans un second terminal : test de bout en bout
pnpm smoke
```

Résultat attendu de `pnpm smoke` :

```text
1. Santé des services
   ✔ catalog (http://localhost:3001)
   ✔ identity (http://localhost:3002)
   ✔ stats (http://localhost:3003)
2. Publication d'un ping par catalog
   ✔ eventId=... partition=2 offset=0
3. Réception par stats via Kafka
   ✔ reçu en 322 ms : partition=2 offset=0 (total reçu : 1)

✅ Smoke test réussi : l'événement a traversé Kafka de catalog à stats.
```

> Au tout premier lancement, les images Docker sont téléchargées : environ 240 Mo pour `apache/kafka:4.3.2` et quelques centaines de Mo pour Kafbat UI (620 Mo une fois décompressée). `postgres:16-alpine` est réutilisée si elle est déjà présente. Voir [§ 5](#5-partager-les-images-docker-sans-internet) pour éviter ce téléchargement.

### Explorer

| Quoi | Où |
| --- | --- |
| Kafbat UI : topics, messages, groupes | http://localhost:8080 |
| Documentation interactive des API (OpenAPI) | http://localhost:3001/docs, http://localhost:3002/docs, http://localhost:3003/docs |
| Publier un ping | `curl.exe -X POST localhost:3001/dev/ping` |
| Publier avec une clé (même clé, donc même partition) | `curl.exe -X POST localhost:3001/dev/ping -H "content-type: application/json" -d '{\"key\":\"abc\"}'` |
| Compteur de stats | `curl.exe localhost:3003/stats/pings` |

### Expérience à faire : stats rattrape son retard

1. Dans le terminal de `pnpm dev`, arrêtez tout avec **Ctrl+C**, puis relancez **seulement** catalog : `cd services/catalog; uv run python -m catalog_service`.
2. Publiez 3 pings : `curl.exe -X POST localhost:3001/dev/ping` (trois fois).
3. Relancez stats : `cd services/stats; uv run python -m stats_service`.
4. `curl.exe localhost:3003/stats/pings` : `count` vaut 3, car stats a repris à ses offsets commités.

---

## 3. Commandes

| Commande | Effet |
| --- | --- |
| `pnpm setup` | Installe ou met à jour l'environnement Python (`uv sync --all-packages`) |
| `pnpm dev` | Lance catalog (3001), identity (3002) et stats (3003), avec rechargement auto |
| `pnpm typecheck` | mypy `--strict` dans tous les projets Python |
| `pnpm lint` | ruff (lint et format) |
| `pnpm test` | pytest dans tous les projets (sans Kafka) |
| `pnpm smoke` | Test de bout en bout (infra et services démarrés) |
| `pnpm infra:up` | Démarre l'infrastructure (ne télécharge que les images absentes) |
| `pnpm infra:down` | Arrête l'infrastructure (les données sont conservées) |
| `pnpm infra:reset` | Supprime les volumes (données Kafka et Postgres) puis redémarre |
| `pnpm infra:logs` | Suit les journaux des conteneurs |

Dans un seul projet : `cd services/stats` puis `uv run pytest`, `uv run mypy src tests`, `uv run python -m stats_service`.

---

## 4. Dépannage

### Un port est déjà occupé

Symptôme : `Bind for 0.0.0.0:5432 failed: port is already allocated`, ou un service qui ne démarre pas (`[Errno 10048]`).

```powershell
# Qui utilise le port ?
Get-NetTCPConnection -LocalPort 5433 -State Listen | Select-Object LocalPort, OwningProcess
Get-Process -Id <PID>
```

- **Ports Docker** (Kafka 9092, Kafbat 8080, Postgres 5433) : changez la valeur dans `.env` (`POSTGRES_PORT=5434`…), puis `pnpm infra:down` et `pnpm infra:up`. Si vous changez `KAFKA_PORT`, changez aussi `KAFKA_BROKERS=localhost:<port>`.
- **Ports des services** (3001-3003) : changez `CATALOG_PORT`, `IDENTITY_PORT` et `STATS_PORT` dans `.env`.
- Le port **5432** est souvent pris par un PostgreSQL installé localement, ou dans WSL : c'est pour cela que StreamLab utilise **5433** par défaut.

### Des processus Python restent après l'arrêt de `pnpm dev`

Avec Ctrl+C dans le terminal, tout s'arrête proprement. Si le terminal a été fermé brutalement, des `python.exe` peuvent garder les ports 3001-3003 :

```powershell
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -match '_service' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
```

> Après un arrêt **forcé** de stats, son redémarrage peut prendre jusqu'à environ 45 s : le groupe `stats-service` attend que l'ancien membre « fantôme » expire (`session.timeout.ms`). Après un Ctrl+C, c'est immédiat.

### `kafka-init` n'a pas créé le topic

```powershell
docker compose ps -a              # kafka-init doit être « Exited (0) »
docker compose logs kafka-init
docker compose up kafka-init      # relance (idempotent grâce à --if-not-exists)
```

Erreur `/bin/bash^M: bad interpreter` : le script a des fins de ligne CRLF. Le `.gitattributes` force LF ; si le dépôt a été cloné avant, exécutez `git add --renormalize .` ou reclonez.

### Commande `docker compose exec ... /opt/kafka/...` qui échoue dans Git Bash

Git Bash convertit les chemins Unix (`/opt/kafka/...` devient `C:/Program Files/Git/opt/kafka/...`). Préfixez la commande, ou utilisez PowerShell :

```bash
MSYS_NO_PATHCONV=1 docker compose exec kafka /opt/kafka/bin/kafka-topics.sh --bootstrap-server kafka:19092 --describe --topic system.ping
```

### `pnpm smoke` échoue à l'étape 3 (timeout)

- Stats vient de démarrer : il attend peut-être l'attribution de ses partitions (voir « membre fantôme » ci-dessus). Relancez `pnpm smoke`.
- Kafka est-il *healthy* ? `docker compose ps`.
- `KAFKA_BROKERS` dans `.env` doit valoir `localhost:<KAFKA_PORT>` : les services tournent sur l'hôte et utilisent le listener HOST.

### Les scripts PostgreSQL ne se sont pas exécutés

Ils ne tournent **qu'au premier démarrage** (volume vide). Pour les rejouer : `pnpm infra:reset` (⚠ supprime les données).

---

## 5. Partager les images Docker sans Internet

Pour éviter que chaque étudiant télécharge environ 1 Go, une personne exporte les images et les partage par clé USB ou sur le réseau local :

```powershell
# Sur la machine qui a les images
docker save -o streamlab-images.tar apache/kafka:4.3.2 ghcr.io/kafbat/kafka-ui:v1.5.1 postgres:16-alpine

# Sur chaque autre machine
docker load -i streamlab-images.tar
docker images                     # les trois images apparaissent
pnpm infra:up                     # aucun téléchargement : les images sont présentes
```

De même, le cache uv (`uv cache dir`) et le store pnpm (`pnpm store path`) peuvent être copiés pour une installation hors ligne.

---

## 6. Structure du dépôt

```
apps/                    # interfaces (Next.js au TD2)
packages/contracts/      # topics, enveloppe d'événement, schémas (Python, Pydantic)
packages/kafka/          # publisher idempotent, consumer validant (confluent-kafka)
services/catalog/        # :3001 — publie system.ping
services/identity/       # :3002 — squelette
services/stats/          # :3003 — consomme system.ping (groupe stats-service)
infra/                   # create-topics.sh, init PostgreSQL
scripts/smoke-test.mjs   # pnpm smoke
docs/                    # vision, architecture, ADR
```

Pile : pnpm + Turborepo (orchestration), uv (Python), FastAPI, Pydantic v2, confluent-kafka, pytest, mypy, ruff, Kafka 4.3.2 (KRaft), Kafbat UI 1.5.1, PostgreSQL 16. Les raisons de ces choix sont dans les [ADR](docs/adr/).

## 7. Contribuer

Lire [`AGENTS.md`](AGENTS.md) : une branche et une PR par tâche, plan avant le code, tests d'abord, aucun test affaibli, aucune donnée réelle ni aucun secret, nouvelles dépendances vérifiées, ADR pour tout nouveau topic, framework ou pattern. Le modèle de PR contient la liste de contrôle.
