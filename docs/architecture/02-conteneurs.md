# 2. Conteneurs (C4 niveau 2)

> **Question :** quelles applications et quelles bases composent StreamLab, et comment communiquent-elles ?
> Un « conteneur », au sens C4, est une unité qui s'exécute ou qui stocke des données : application web, service, base, broker. Ce n'est pas forcément un conteneur Docker.

## 2.1 Architecture cible

```mermaid
flowchart LR
    user["👤 Utilisateurs"]

    subgraph front["Interface"]
        web["apps/web<br/>Next.js 16 (App Router)<br/><i>TD2</i>"]
    end

    gateway["Passerelle d'API<br/>routage, JWT, limitation de débit<br/><i>TD2 / TD5</i>"]

    subgraph services["Microservices (Python, FastAPI)"]
        identity["identity<br/><i>comptes, rôles, JWT</i>"]
        catalog["catalog<br/><i>chaînes, vidéos, recherche</i>"]
        upload["upload<br/><i>URL pré-signées</i>"]
        transcoding["transcoding (workers)<br/><i>FFmpeg → HLS</i>"]
        stats["stats<br/><i>vues, interruptions</i>"]
        modules["modules des groupes<br/><i>chat, direct, premium…</i>"]
    end

    kafka{{"Kafka (KRaft)<br/>bus d'événements"}}

    subgraph data["Une base PostgreSQL par service"]
        db_identity[("identity")]
        db_catalog[("catalog")]
        db_stats[("stats")]
    end

    s3[("Stockage objet S3<br/>Garage / SeaweedFS")]
    mediamtx["MediaMTX<br/><i>direct</i>"]

    user --> web --> gateway
    gateway -->|REST| identity & catalog & upload & stats & modules
    identity --- db_identity
    catalog --- db_catalog
    stats --- db_stats
    upload & catalog & transcoding & stats & identity & modules <-->|événements| kafka
    upload -->|URL pré-signée| s3
    transcoding <-->|lit l'original,<br/>écrit HLS| s3
    modules -.-> mediamtx
```

Règles qui se lisent sur ce schéma :
- **l'interface ne parle qu'à la passerelle** ;
- **entre services, on communique par événements Kafka** (asynchrone). Le REST est réservé à l'entrée par la passerelle ;
- **chaque service a sa base** : aucune flèche ne relie un service à la base d'un autre.

## 2.2 État au TD1 (ce qui existe réellement)

```mermaid
flowchart LR
    dev["👩‍💻 Développeur<br/>(curl, pnpm smoke)"]

    subgraph host["Machine hôte — lancés par pnpm dev (uvicorn)"]
        catalog["catalog :3001<br/>GET /health<br/>POST /dev/ping"]
        identity["identity :3002<br/>GET /health"]
        stats["stats :3003<br/>GET /health<br/>GET /stats/pings"]
    end

    subgraph docker["Docker Compose"]
        kafka{{"kafka<br/>apache/kafka:4.3.2<br/>:9092 (HOST) · :19092 (DOCKER)"}}
        init["kafka-init<br/><i>usage unique :<br/>crée system.ping</i>"]
        ui["kafka-ui (Kafbat)<br/>:8080"]
        pg[("postgres :5433<br/>bases catalog,<br/>identity, stats")]
    end

    dev -->|HTTP| catalog & identity & stats
    catalog -->|"publie system.ping<br/>(localhost:9092)"| kafka
    kafka -->|"groupe stats-service"| stats
    init -->|"kafka:19092"| kafka
    ui -->|"kafka:19092"| kafka
    dev -->|navigateur| ui
```

| Conteneur | Technologie | Rôle au TD1 | Port |
| --- | --- | --- | --- |
| `services/catalog` | FastAPI + uvicorn | Publie `system.ping` | 3001 |
| `services/identity` | FastAPI + uvicorn | Squelette (`/health`) | 3002 |
| `services/stats` | FastAPI + uvicorn + thread consommateur | Consomme `system.ping`, compte les pings | 3003 |
| `kafka` | Apache Kafka 4.3.2, KRaft, un nœud | Broker et controller | 9092 |
| `kafka-init` | même image | Crée les topics puis s'arrête | — |
| `kafka-ui` | Kafbat UI v1.5.1 | Observer topics, messages, groupes | 8080 |
| `postgres` | PostgreSQL 16 | Bases créées, pas encore utilisées | 5433 |

Les bibliothèques partagées ne sont pas des conteneurs : `packages/contracts` (contrats d'événements) et `packages/kafka` (publisher/consumer) sont **importées** par les services.

### Pourquoi les services ne sont-ils pas dans Docker ?
Au TD1, les lancer sur l'hôte avec uvicorn donne un rechargement instantané, des journaux lisibles et un débogage facile, sans construire d'image : c'est aussi plus économe en données. Ils seront conteneurisés au TD6 (déploiement). Ils utilisent donc le listener **HOST** de Kafka (`localhost:9092`) ; voir [infrastructure locale](04-infrastructure-locale.md).
