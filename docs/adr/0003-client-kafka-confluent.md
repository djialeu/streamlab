# ADR 0003 — Client Kafka `confluent-kafka`, API synchrone stable

- **Statut** : accepté
- **Date** : 2026-11-27
- **TD concerné** : TD1

## Contexte

Les services Python doivent produire et consommer des messages Kafka avec : un producteur idempotent, des groupes de consommateurs, un commit manuel des offsets, et le support de Kafka 4. Le client doit être maintenu, gratuit, et installable sous Windows **sans compilateur**.

Le cahier des charges initial (en TypeScript) imposait le client Confluent plutôt que `kafkajs`, qui n'est plus maintenu. Le même raisonnement s'applique en Python.

## Options envisagées

### Option A — `confluent-kafka` (retenue)
- Client officiel de Confluent, basé sur **librdkafka** (C), le moteur de référence partagé par les clients Go, .NET et JS de Confluent.
- Roues précompilées pour Windows, Linux et macOS, y compris Python 3.14 (vérifié : 2.16.2 du 18/11/2026).
- Typé (`py.typed`, `cimpl.pyi`), ce qui est compatible avec mypy strict.
- L'API asyncio (`confluent_kafka.aio`) existe, mais elle est **marquée « experimental »**.

### Option B — `aiokafka`
- Avantages : nativement asyncio, s'intègre directement à FastAPI.
- Inconvénients : réimplémentation en pur Python du protocole, qui suit les nouveautés de Kafka avec du retard ; ce n'est pas le moteur de référence.

### Option C — `kafka-python`
- Inconvénients : historique de maintenance irrégulier ; synchrone et moins performant.

## Décision

**`confluent-kafka`**, avec son **API synchrone stable** (et non `confluent_kafka.aio`, expérimentale), encapsulée dans `packages/kafka` :

- **producteur** : `enable.idempotence=True` ; `publish()` attend l'accusé (`flush`) et s'appelle depuis FastAPI via `asyncio.to_thread` ;
- **consommateur** : boucle `poll()` dans un **thread dédié** démarré et arrêté par le lifespan FastAPI ; `enable.auto.commit=False` et commit **après** traitement ; `auto.offset.reset=earliest` ; `close()` à l'arrêt.

## Conséquences

- **Positives** : moteur éprouvé ; même sémantique que les clients Confluent des autres langages ; aucune compilation nécessaire.
- **Négatives** : mélange de threads et d'asyncio, d'où la nécessité de protéger l'état partagé par un verrou ; `publish` envoie et attend message par message (simple, mais lent à fort débit).
- **À revoir** : passer à `confluent_kafka.aio` quand elle sortira du statut expérimental ; regrouper les envois (sans `flush` par message) si un module a besoin de débit.
