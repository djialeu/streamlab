# Vision de StreamLab

> Document de référence permanent. Il décrit **où va** le projet ; l'état réel du code est décrit dans [`docs/architecture/`](architecture/README.md).

## Sommaire

1. [Pourquoi ce projet existe](#1-pourquoi-ce-projet-existe)
2. [Vision du produit](#2-vision-du-produit)
3. [Utilisateurs et rôles](#3-utilisateurs-et-rôles)
4. [Fonctionnalités visées](#4-fonctionnalités-visées)
5. [Architecture cible](#5-architecture-cible)
6. [Exigences non fonctionnelles](#6-exigences-non-fonctionnelles)
7. [Feuille de route des TD](#7-feuille-de-route-des-td)

---

## 1. Pourquoi ce projet existe

StreamLab est le projet fil rouge du cours **« Technologie web et applications »** (Master 2 Génie logiciel).

- Toute la promotion construit **une seule application**.
- Les **six TD** construisent un socle commun.
- Ensuite, **10 à 15 groupes** d'étudiants ajoutent chacun un module ou un service dans le même dépôt, puis le présentent en exposé.

Le code sert de **référence aux étudiants**. Il doit être clair, commenté en français et sans complexité inutile. On préfère toujours le code lisible au code astucieux.

## 2. Vision du produit

StreamLab est une plateforme de **streaming vidéo éducative**, sur le modèle simplifié de YouTube et Twitch.

- Des **créateurs** publient des vidéos à la demande et animent des directs.
- Des **spectateurs** parcourent le catalogue, regardent les vidéos dans une qualité qui s'adapte à leur connexion, discutent pendant les directs et peuvent s'abonner à des contenus premium.

## 3. Utilisateurs et rôles

| Rôle | Ce qu'il peut faire |
| --- | --- |
| Visiteur | Parcourir le catalogue public, regarder les vidéos gratuites |
| Spectateur inscrit | En plus : historique, reprise de lecture, chat des directs, abonnements |
| Créateur | Gérer sa chaîne, envoyer des vidéos, lancer des directs, consulter ses statistiques |
| Administrateur | Modérer les contenus et les comptes |

## 4. Fonctionnalités visées

Vue d'ensemble : tout n'est pas à faire maintenant.

1. **Catalogue** : chaînes, vidéos, recherche, fiche vidéo.
2. **Envoi et transcodage** : envoi direct vers le stockage par URL pré-signée, transcodage FFmpeg en HLS (360p, 720p, 1080p), suivi du statut (en attente, en cours, prête, en échec).
3. **Lecture adaptative** : lecteur hls.js, changement de qualité automatique, reprise de lecture, mesures de qualité d'expérience (temps de démarrage, interruptions).
4. **Comptes et rôles** : service d'identité, jetons JWT vérifiés à la passerelle.
5. **Statistiques** : vues et interruptions, calculées à partir des événements de lecture.
6. **Modules ajoutés par les groupes** : direct (WebRTC, LL-HLS), chat temps réel, abonnements premium, recherche dans les vidéos par IA, serveur MCP, PWA hors ligne, observabilité, sagas, traitement de flux, registre de schémas, CQRS, Kubernetes, etc.

## 5. Architecture cible

| Élément | Choix |
| --- | --- |
| **Interface** | Next.js 16 (App Router). Elle ne parle qu'à la passerelle d'API. |
| **Passerelle d'API** | Routage, vérification des jetons, limitation de débit. |
| **Microservices** | Python, **FastAPI**, Pydantic v2 : identity, catalog, upload, transcoding (workers), stats, puis les services ajoutés par les groupes. *(Le cahier des charges initial prévoyait Node.js/Fastify ; voir [ADR 0005](adr/0005-fastapi-pour-les-services.md).)* |
| **Données** | **Une base PostgreSQL par service.** Un service n'accède jamais à la base d'un autre : il passe par son API ou par ses événements. |
| **Communication** | Requêtes synchrones (REST) entre l'interface et les services via la passerelle ; communication asynchrone par **événements Kafka** entre services. |
| **Topics prévus** | `video.uploaded`, `video.transcoded`, `video.published`, `playback.events`, `user.registered`, créés au fil des TD. Convention : `<domaine>.<événement au passé>`. |
| **Stockage des vidéos** | Stockage objet compatible S3, auto-hébergé (Garage ou SeaweedFS ; pas MinIO, dont l'édition communautaire est en mode maintenance). |
| **Médias** | FFmpeg pour le transcodage, MediaMTX pour le direct. |
| **Patterns introduits plus tard** | Outbox, file des messages en erreur (DLQ), sagas, registre de schémas, tests de contrat. |
| **Modules de groupe** | Chacun est activable par *feature flag*, sans casser les autres. |

## 6. Exigences non fonctionnelles

- Fonctionne sur des ordinateurs d'étudiants modestes (**8 à 16 Go de RAM**), sous Windows, macOS ou Linux, avec Docker.
- **100 % gratuit et open source.**
- **Économe en données** : les connexions sont limitées et souvent payées au volume.
- Documentation et commentaires **en français** ; identifiants du code **en anglais**.
- Développement assisté par des agents de code, sous des règles strictes (voir [AGENTS.md](../AGENTS.md)).

## 7. Feuille de route des TD

| TD | Contenu |
| --- | --- |
| **TD1** | Socle : monorepo, infrastructure Docker, trois services squelettes, un événement de test qui traverse Kafka |
| TD2 | Service catalogue avec sa base, passerelle d'API, interface Next.js |
| TD3 | Envoi et transcodage pilotés par événements (`video.uploaded` → workers → `video.transcoded`) |
| TD4 | Lecture adaptative et événements de lecture agrégés par le service stats |
| TD5 | Service identité, sécurité entre services, tests de contrat, CI bloquante |
| TD6 | Outbox, DLQ et reprises, déploiement, gabarit de module pour les groupes |
