#!/usr/bin/env bash
# Crée une base et un utilisateur par service (règle : une base par service).
# Exécuté UNE SEULE FOIS par l'image postgres, au premier démarrage
# (volume vide). Pour le rejouer : pnpm infra:reset (supprime les données).
#
# Les mots de passe viennent des variables d'environnement (voir .env.example).
set -euo pipefail

# create_service_db <nom> <mot_de_passe>
create_service_db() {
  local name="$1"
  local password="$2"
  echo "-> base et utilisateur « ${name} »"
  psql -v ON_ERROR_STOP=1 --username "${POSTGRES_USER}" --dbname postgres \
    -v name="${name}" -v password="${password}" <<'SQL'
-- Utilisateur du service : il peut se connecter, rien de plus.
CREATE ROLE :"name" LOGIN PASSWORD :'password';
-- La base appartient à l'utilisateur du service.
CREATE DATABASE :"name" OWNER :"name";
-- Par défaut, PUBLIC (tout le monde) peut se connecter à toute base :
-- on retire ce droit pour que seul le propriétaire y accède.
REVOKE ALL ON DATABASE :"name" FROM PUBLIC;
SQL
}

create_service_db catalog  "${CATALOG_DB_PASSWORD}"
create_service_db identity "${IDENTITY_DB_PASSWORD}"
create_service_db stats    "${STATS_DB_PASSWORD}"

echo "Bases des services créées."
