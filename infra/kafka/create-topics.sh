#!/usr/bin/env bash
# Crée les topics Kafka de StreamLab. Exécuté par le conteneur kafka-init.
#
# Idempotent grâce à --if-not-exists : on peut relancer kafka-init sans erreur.
# Règle du projet : tout nouveau topic passe d'abord par un ADR (docs/adr/),
# puis est ajouté ici ET dans packages/contracts (topics.py).
set -euo pipefail

BOOTSTRAP_SERVER="${BOOTSTRAP_SERVER:-kafka:19092}"
KAFKA_TOPICS=/opt/kafka/bin/kafka-topics.sh

# create_topic <nom> <partitions>
create_topic() {
  local name="$1"
  local partitions="$2"
  echo "-> topic ${name} (${partitions} partitions)"
  "${KAFKA_TOPICS}" --bootstrap-server "${BOOTSTRAP_SERVER}" \
    --create --if-not-exists \
    --topic "${name}" \
    --partitions "${partitions}" \
    --replication-factor 1
}

echo "Création des topics sur ${BOOTSTRAP_SERVER}..."

# TD1 : topic de test qui prouve qu'un événement traverse Kafka.
create_topic system.ping 3

echo "Topics présents :"
"${KAFKA_TOPICS}" --bootstrap-server "${BOOTSTRAP_SERVER}" --list
echo "kafka-init terminé."
