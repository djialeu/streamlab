# Prompt TD1 — Socle de StreamLab

Ce fichier contient d'abord le **contexte permanent** du projet (à conserver dans le dépôt), puis la **tâche du TD1**.

---

# Partie 1 — Contexte permanent du projet

## Pourquoi ce projet existe

StreamLab est le projet fil rouge du cours « Technologie web et applications » (Master 2 Génie logiciel). Toute la promotion construit **une seule application**. Les six TD construisent un socle commun. Ensuite, 10 à 15 groupes d'étudiants ajoutent chacun un module ou un service dans le même dépôt, puis le présentent en exposé.

Le code que tu produis sert de **référence aux étudiants** : il doit être clair, commenté en français, sans complexité inutile. Préfère toujours le code lisible au code astucieux.

## Vision du produit

StreamLab est une plateforme de streaming vidéo éducative, sur le modèle simplifié de YouTube et Twitch. Des créateurs publient des vidéos à la demande et animent des directs. Des spectateurs parcourent le catalogue, regardent les vidéos dans une qualité qui s'adapte à leur connexion, discutent pendant les directs et peuvent s'abonner à des contenus premium.

## Utilisateurs et rôles

| Rôle | Ce qu'il peut faire |
| --- | --- |
| Visiteur | Parcourir le catalogue public, regarder les vidéos gratuites |
| Spectateur inscrit | En plus : historique, reprise de lecture, chat des directs, abonnements |
| Créateur | Gérer sa chaîne, envoyer des vidéos, lancer des directs, consulter ses statistiques |
| Administrateur | Modérer les contenus et les comptes |

## Fonctionnalités visées (vue d'ensemble — tout n'est pas à faire maintenant)

1. **Catalogue** : chaînes, vidéos, recherche, fiche vidéo.
2. **Envoi et transcodage** : envoi direct vers le stockage par URL pré-signée, transcodage FFmpeg en HLS (360p, 720p, 1080p), suivi du statut (en attente, en cours, prête, en échec).
3. **Lecture adaptative** : lecteur hls.js, changement de qualité automatique, reprise de lecture, mesures de qualité d'expérience (temps de démarrage, interruptions).
4. **Comptes et rôles** : service d'identité, jetons JWT vérifiés à la passerelle.
5. **Statistiques** : vues et interruptions, calculées à partir des événements de lecture.
6. **Modules ajoutés par les groupes** : direct (WebRTC, LL-HLS), chat temps réel, abonnements premium, recherche dans les vidéos par IA, serveur MCP, PWA hors ligne, observabilité, sagas, traitement de flux, registre de schémas, CQRS, Kubernetes, etc.

## Architecture cible

- **Interface** : Next.js 16 (App Router), qui ne parle qu'à la passerelle d'API.
- **Passerelle d'API** : routage, vérification des jetons, limitation de débit.
- **Microservices** (Node.js, TypeScript, Fastify) : identity, catalog, upload, transcoding (workers), stats, puis les services ajoutés par les groupes.
- **Une base PostgreSQL par service.** Un service n'accède jamais à la base d'un autre : il passe par son API ou par ses événements.
- **Communication** : requêtes synchrones (REST) entre l'interface et les services via la passerelle ; communication asynchrone par **événements Kafka** entre services.
- **Topics prévus**, créés au fil des TD : `video.uploaded`, `video.transcoded`, `video.published`, `playback.events`, `user.registered`. Convention : `<domaine>.<événement au passé>`.
- **Stockage des vidéos** : stockage objet compatible S3, auto-hébergé (Garage ou SeaweedFS ; pas MinIO, dont l'édition communautaire est en mode maintenance).
- **Médias** : FFmpeg pour le transcodage, MediaMTX pour le direct.
- **Patterns introduits plus tard** : outbox, file des messages en erreur (DLQ), sagas, registre de schémas, tests de contrat.
- **Chaque module de groupe est activable par feature flag**, sans casser les autres.

## Exigences non fonctionnelles

- Fonctionne sur des ordinateurs d'étudiants modestes (8 à 16 Go de RAM), sous Windows, macOS ou Linux, avec Docker.
- 100 % gratuit et open source.
- Économe en données : connexions limitées et souvent payées au volume.
- Documentation et commentaires en français ; identifiants du code en anglais.
- Développement assisté par des agents de code, sous des règles strictes (voir AGENTS.md).

## Feuille de route des TD

| TD | Contenu |
| --- | --- |
| **TD1** | **Socle : monorepo, infrastructure Docker, trois services squelettes, un événement de test qui traverse Kafka (cette tâche)** |
| TD2 | Service catalogue avec sa base, passerelle d'API, interface Next.js |
| TD3 | Envoi et transcodage pilotés par événements (`video.uploaded` → workers → `video.transcoded`) |
| TD4 | Lecture adaptative et événements de lecture agrégés par le service stats |
| TD5 | Service identité, sécurité entre services, tests de contrat, CI bloquante |
| TD6 | Outbox, DLQ et reprises, déploiement, gabarit de module pour les groupes |

---

# Partie 2 — Tâche actuelle : TD1 uniquement

Je suis sous **Windows avec Docker Desktop** (backend WSL 2). Le dossier est vide.

**Ne code que le TD1.** N'anticipe pas les fonctionnalités des TD suivants. Choisis en revanche une structure qui les accueillera sans refonte (dossiers `apps/`, `services/`, `packages/`).

## Objectif

Mettre en place le monorepo, l'infrastructure locale et trois services squelettes, et prouver qu'un événement traverse Kafka d'un service à un autre.

## Pile imposée

- Monorepo pnpm (workspaces) + Turborepo, TypeScript strict, modules ESM.
- Services Node.js avec Fastify 5, lancés en local avec tsx (pas dans Docker pour l'instant).
- Validation des données avec zod 4.
- Client Kafka : `@confluentinc/kafka-javascript` (son API compatible KafkaJS). N'utilise **pas** le paquet `kafkajs`, qui n'est plus maintenu. Attention : pnpm 10 bloque les scripts d'installation ; ce client doit être autorisé dans `onlyBuiltDependencies` (pnpm-workspace.yaml).
- Infrastructure dans Docker Compose :
  - **Kafka 4 en mode KRaft** (sans ZooKeeper), image officielle `apache/kafka:4.3.2`, un seul nœud broker + controller. Inspire-toi de l'exemple officiel single-node du dépôt apache/kafka (`docker/examples`). Deux listeners : un pour l'hôte (`localhost:9092`), un interne pour les conteneurs. Désactive la création automatique des topics. Limite la mémoire (`KAFKA_HEAP_OPTS`). Ajoute un healthcheck. Données dans un volume nommé.
  - **Un conteneur `kafka-init` à usage unique** qui crée les topics avec `kafka-topics.sh --if-not-exists`, à partir d'un script `infra/kafka/create-topics.sh`. Pour l'instant, un seul topic : `system.ping`, 3 partitions.
  - **Kafbat UI** (`ghcr.io/kafbat/kafka-ui`) sur le port 8080, démarrée par défaut avec le reste, mémoire limitée. Épingle une version précise (pas `latest`).
  - **PostgreSQL** avec un script d'initialisation qui crée une base et un utilisateur par service (catalog, identity, stats), chaque utilisateur limité à sa propre base.
  - Tous les ports configurables via `.env` (fournis un `.env.example`).

## Structure attendue

- `packages/contracts` : noms des topics ; enveloppe d'événement commune (`eventId` UUID, `type`, `version`, `occurredAt` ISO, `source`, `payload`) ; `createEvent` ; `parseEvent`, qui valide l'enveloppe puis le payload ; schéma du payload de `system.ping`. Avec des tests Vitest.
- `packages/kafka` : petite couche au-dessus du client : `createPublisher` (producteur idempotent ; la clé du message détermine la partition) et `startConsumer` (groupe de consommateurs, validation de chaque message ; un message invalide est journalisé puis ignoré, sans bloquer la partition).
- `services/catalog` (port 3001) : `GET /health` et `POST /dev/ping`, qui publie un événement `system.ping`.
- `services/stats` (port 3003) : consomme `system.ping` dans le groupe `stats-service`, de façon idempotente (un `eventId` déjà vu est ignoré), et expose `GET /stats/pings` (nombre reçu, dernier événement avec partition et offset).
- `services/identity` (port 3002) : squelette avec `GET /health` seulement.
- Chaque service s'arrête proprement sur SIGINT et SIGTERM.
- `scripts/smoke-test.mjs` (commande `pnpm smoke`) : vérifie que les trois services répondent, publie un ping, puis vérifie qu'il arrive dans stats en moins de 10 secondes.

## Documentation et gouvernance

- **`docs/vision.md`** : reprends la Partie 1 de ce document, mise en forme.
- **`AGENTS.md`** (en français), lu par tous les agents de code :
  - résumé de la vision et de l'architecture cible, avec un lien vers `docs/vision.md` ;
  - pile, structure du dépôt, commandes ;
  - conventions : nommage des topics, enveloppe d'événement, consommateurs idempotents, une base par service ;
  - règles de travail : une branche et une PR par tâche ; plan avant le code ; tests d'abord ; ne jamais supprimer ou affaiblir un test pour le faire passer ; aucun secret ni donnée réelle ; toute nouvelle dépendance vérifiée sur npm (existence, maintenance) et justifiée ; pas de nouveau topic, framework ou pattern sans ADR ;
  - feuille de route des TD, en précisant l'étape en cours.
- **`CLAUDE.md`** : une seule ligne, `@AGENTS.md`, pour que Claude Code charge AGENTS.md à chaque session.
- **`.github/pull_request_template.md`**, avec cette liste de contrôle : diff lu et compris ; critères d'acceptation vérifiés ; tests qui passent sans test affaibli ; dépendances vérifiées ; aucun secret ni donnée réelle ; architecture respectée ; outil IA et parties générées indiqués ; scénario testé manuellement.
- **`.github/workflows/ci.yml`** : installation pnpm, typecheck et tests sur chaque push et chaque PR.
- **`docs/adr/0001-microservices-et-kafka.md`** : premier ADR qui justifie le choix microservices + Kafka (contexte, options envisagées, décision, conséquences).
- **`README.md`** (en français) : démarrage pas à pas sous Windows (prérequis, `corepack enable` pour pnpm, réglage de la mémoire WSL via `.wslconfig`, commandes, dépannage des ports déjà occupés, partage des images Docker par `docker save` / `docker load`).
- **`.gitattributes`** qui force les fins de ligne LF (les scripts `.sh` et `.sql` s'exécutent dans des conteneurs Linux) ; **`.gitignore`** qui exclut `.env` et `node_modules`.
- **Scripts racine** : `dev`, `typecheck`, `test`, `infra:up`, `infra:down`, `infra:reset`, `infra:logs`, `smoke`.

## Économie de données (important : ma connexion est limitée)

- Avant toute chose, liste les images Docker déjà présentes (`docker images`) et les versions installées (`node -v`, `pnpm -v`, `git --version`). Réutilise ce qui est déjà là.
- **PostgreSQL** : utilise le tag de l'image postgres déjà présente sur ma machine. Toute version récente de PostgreSQL convient.
- **Node.js** : utilise la version installée si elle est supérieure ou égale à 20, et adapte `.nvmrc` et `engines` en conséquence. Ne propose une mise à jour que si elle est vraiment nécessaire, en expliquant pourquoi. Aucune image Docker Node n'est nécessaire à cette étape.
- N'utilise jamais le tag `latest` : épingle des versions précises.
- Ne lance jamais `docker compose pull` ni `--pull always` : `docker compose up` ne télécharge que les images absentes.
- **Avant de télécharger quoi que ce soit** (image Docker, nouvelle version de Node ou de pnpm), donne-moi la liste de ce qui manque, avec la taille approximative, et attends mon accord.
- Pour les paquets npm, utilise `pnpm install --prefer-offline`.

## Façon de travailler

1. Lis tout ce document, fais l'inventaire de ma machine (section précédente), puis présente-moi ton plan et la liste des fichiers. **Attends ma validation.**
2. Fais `git init`, puis avance par étapes, avec un commit à chaque étape qui fonctionne.
3. Avant d'installer un paquet, vérifie qu'il existe et qu'il est maintenu ; utilise des versions récentes et stables.
4. À la fin, lance toi-même : `pnpm install`, `pnpm typecheck`, `pnpm test`, `pnpm infra:up` ; vérifie que `kafka-init` a créé le topic ; lance les services ; exécute `pnpm smoke`. Corrige jusqu'à ce que tout passe.
5. Termine par un résumé : ce qui a été créé, les commandes pour tout relancer, et 5 questions que je pourrais poser aux étudiants pour vérifier qu'ils ont compris ce socle (partitions, groupes de consommateurs, idempotence, base par service, listeners Kafka).

## Critères d'acceptation du TD1

- [ ] `docker compose up -d` démarre Kafka, Kafbat UI et PostgreSQL ; `kafka-init` crée `system.ping` avec 3 partitions, puis s'arrête.
- [ ] Les trois services démarrent avec `pnpm dev` et répondent sur `/health`.
- [ ] `pnpm smoke` réussit : le ping publié par catalog arrive dans stats, avec sa partition et son offset.
- [ ] Dans Kafbat UI, le topic `system.ping` et le groupe `stats-service` sont visibles.
- [ ] Si stats est arrêté pendant que des pings sont publiés, il les récupère tous au redémarrage.
- [ ] `pnpm typecheck` et `pnpm test` passent ; la CI GitHub Actions est configurée.
- [ ] AGENTS.md, CLAUDE.md, `docs/vision.md`, le README et l'ADR 0001 existent et sont à jour.
