# ADR 0001 — Microservices communiquant par événements Kafka

- **Statut** : accepté
- **Date** : 2026-11-27
- **Auteurs** : équipe enseignante
- **TD concerné** : TD1 (socle)

## Contexte

StreamLab est construit par **toute une promotion** : six TD posent un socle, puis **10 à 15 groupes** ajoutent chacun un module ou un service dans le même dépôt, et le présentent en exposé. Le projet doit :

- permettre à des groupes de travailler **en parallèle**, sans se bloquer ni casser le travail des autres ;
- rendre chaque module **activable ou désactivable** (feature flag) ;
- illustrer les notions du cours : services distribués, communication asynchrone, idempotence, sagas, outbox, CQRS, traitement de flux ;
- tourner sur des **machines d'étudiants modestes** (8 à 16 Go), gratuitement.

Plusieurs traitements sont naturellement **asynchrones** : transcodage d'une vidéo (plusieurs minutes), agrégation des statistiques de lecture, notifications.

## Options envisagées

### Option A — Monolithe modulaire (une application, une base)
- Avantages : le plus simple à lancer et à déboguer ; transactions locales ; le moins gourmand en mémoire.
- Inconvénients : 15 groupes dans la même application et la même base, d'où des conflits permanents et un couplage par les tables ; ne permet pas d'enseigner la communication entre services, l'idempotence, les sagas ; un module défaillant peut faire tomber l'ensemble.

### Option B — Microservices appelés en REST synchrone uniquement
- Avantages : modèle familier, facile à tracer.
- Inconvénients : couplage temporel (si stats est arrêté, catalog échoue ou doit gérer des reprises) ; chaînes d'appels fragiles ; ajouter un consommateur oblige à modifier le producteur.

### Option C — Microservices + bus d'événements Kafka (retenue)
- Avantages : le producteur ne connaît pas ses consommateurs, donc **un groupe ajoute un service en s'abonnant à un topic, sans toucher au code des autres** ; les événements sont **conservés** (un service arrêté rattrape son retard, un nouveau service peut relire l'historique) ; partitions et groupes de consommateurs permettent la montée en charge ; c'est le support naturel de l'outbox, de la DLQ, des sagas, de CQRS et du traitement de flux prévus au programme.
- Inconvénients : plus de pièces à faire tourner (broker JVM) ; cohérence à terme au lieu de transactions ; débogage distribué ; livraison « au moins une fois », donc consommateurs idempotents obligatoires.

### Option D — Microservices + RabbitMQ ou NATS
- Avantages : plus légers que Kafka ; RabbitMQ excelle en files de tâches.
- Inconvénients : la rétention longue et la relecture de l'historique sont moins naturelles (sauf extensions) ; moins adaptés aux modules « traitement de flux », « registre de schémas » et « CQRS » ; Kafka est la référence la plus demandée sur le marché.

## Décision

**Option C.** StreamLab est découpé en **microservices** ; chacun possède **sa propre base PostgreSQL**.

- Interface vers services : **REST** via la passerelle d'API.
- Service vers service : **événements Kafka** (Kafka 4, mode KRaft, sans ZooKeeper).
- Topics nommés `<domaine>.<événement au passé>` ; enveloppe d'événement commune ([ADR 0004](0004-enveloppe-evenement-commune.md)).
- En local : **un seul nœud Kafka** (broker et controller) avec un tas limité à 512 Mo.

## Conséquences

- **Positives** : les groupes travaillent en parallèle en s'abonnant aux topics ; un service arrêté rattrape les événements manqués (vérifié au TD1) ; le socle sert de support à la majorité des notions du cours.
- **Négatives / dette acceptée** : environ 750 Mo de RAM pour l'infrastructure au repos ; complexité supérieure à un monolithe pour des fonctionnalités simples ; il faut apprendre et appliquer les règles d'idempotence et de gestion des messages invalides.
- **À surveiller** : la mémoire sur les machines de 8 Go (limites `mem_limit`, `.wslconfig`) ; la discipline « pas de topic sans ADR » pour éviter la prolifération ; la cohérence à terme, à expliquer dans chaque module.
