#!/usr/bin/env bash

set -Eeuo pipefail

# --------------------------------------------------
# Configuration du projet
# --------------------------------------------------

PROJECT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"

SYNAPSE_IMAGE="matrixdotorg/synapse:v1.163.0"
SERVER_NAME="kibare.test"

DATA_DIR="$PROJECT_DIR/synapse/data"
CONFIG_FILE="$DATA_DIR/homeserver.yaml"
SIGNING_KEY="$DATA_DIR/$SERVER_NAME.signing.key"
ENV_FILE="$PROJECT_DIR/.env"

info() {
    printf '\n[INFO] %s\n' "$1"
}

error() {
    printf '\n[ERREUR] %s\n' "$1" >&2
    exit 1
}

# --------------------------------------------------
# 1. Vérification des prérequis
# --------------------------------------------------

command -v docker >/dev/null 2>&1 \
    || error "Docker n'est pas installé."

command -v openssl >/dev/null 2>&1 \
    || error "OpenSSL est nécessaire."

docker compose version >/dev/null 2>&1 \
    || error "Le plugin Docker Compose est introuvable."

docker info >/dev/null 2>&1 \
    || error "Docker n'est pas accessible."

[ -f compose.yaml ] \
    || error "compose.yaml est introuvable."

[ -f .env.example ] \
    || error ".env.example est introuvable."

info "Prérequis vérifiés."

# --------------------------------------------------
# 2. Préparation des variables d'environnement
# --------------------------------------------------

if [ ! -f "$ENV_FILE" ]; then

    info "Première installation : création du fichier .env."

    DB_PASSWORD="$(openssl rand -hex 32)"

    (
        umask 077
        printf '# Mot de passe PostgreSQL de Kibare\nSYNAPSE_DB_PASSWORD=%s\n' \
            "$DB_PASSWORD" > "$ENV_FILE"
    )

    info "Secret PostgreSQL généré."

else

    info "Fichier .env existant : conservation."

    DB_PASSWORD="$(
        sed -n 's/^SYNAPSE_DB_PASSWORD=//p' "$ENV_FILE" | head -n 1
    )"

    [ -n "$DB_PASSWORD" ] \
        || error "SYNAPSE_DB_PASSWORD est absent ou vide."

    [[ "$DB_PASSWORD" =~ ^[a-f0-9]{64}$ ]] \
        || error "Le mot de passe doit être une chaîne hexadécimale de 64 caractères. Ne le modifie pas sans adapter également la configuration Synapse et PostgreSQL."

fi

# --------------------------------------------------
# 3. Préparation des données Synapse
# --------------------------------------------------

mkdir -p "$DATA_DIR"

if [ -f "$CONFIG_FILE" ] && [ ! -f "$SIGNING_KEY" ]; then
    error "homeserver.yaml existe, mais la clé de signature est absente. Intervention manuelle nécessaire."
fi

if [ ! -f "$CONFIG_FILE" ] && [ -f "$SIGNING_KEY" ]; then
    error "Une clé de signature existe sans homeserver.yaml. Intervention manuelle nécessaire."
fi

# --------------------------------------------------
# 4. Initialisation de Synapse
# --------------------------------------------------

if [ ! -f "$CONFIG_FILE" ]; then

    info "Génération initiale de la configuration Synapse."

    docker pull "$SYNAPSE_IMAGE"

    docker run --rm \
        -v "$DATA_DIR:/data" \
        -e SYNAPSE_SERVER_NAME="$SERVER_NAME" \
        -e SYNAPSE_REPORT_STATS=no \
        "$SYNAPSE_IMAGE" generate

    [ -f "$CONFIG_FILE" ] \
        || error "La génération de homeserver.yaml a échoué."

    [ -f "$SIGNING_KEY" ] \
        || error "La clé de signature n'a pas été générée."

    info "Configuration Synapse générée."

    # Configuration PostgreSQL avec PyYAML.
    docker run --rm -i \
        -v "$DATA_DIR:/data" \
        -e SYNAPSE_DB_PASSWORD="$DB_PASSWORD" \
        --entrypoint python \
        "$SYNAPSE_IMAGE" - <<'PY'
import os
import yaml
from pathlib import Path

path = Path("/data/homeserver.yaml")

config = yaml.safe_load(path.read_text())

config["database"] = {
    "name": "psycopg2",
    "args": {
        "user": "synapse",
        "password": os.environ["SYNAPSE_DB_PASSWORD"],
        "database": "synapse",
        "host": "db",
        "port": 5432,
        "cp_min": 5,
        "cp_max": 10,
    },
}

path.write_text(
    yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
)
PY

    info "Configuration PostgreSQL appliquée."

else

    info "Configuration Synapse existante : conservation."

    # Vérifier que le mot de passe de la configuration correspond
    # à celui du fichier .env, sans afficher le secret.
    docker run --rm -i \
        -v "$DATA_DIR:/data" \
        -e SYNAPSE_DB_PASSWORD="$DB_PASSWORD" \
        --entrypoint python \
        "$SYNAPSE_IMAGE" - <<'PY'
import os
import sys
import yaml
from pathlib import Path

config = yaml.safe_load(
    Path("/data/homeserver.yaml").read_text()
)

database = config.get("database", {})
args = database.get("args", {})

expected = {
    "name": "psycopg2",
    "user": "synapse",
    "database": "synapse",
    "host": "db",
    "port": 5432,
}

if database.get("name") != expected["name"]:
    sys.exit("Le moteur de base de données est incorrect.")

for key, value in expected.items():
    if key == "name":
        continue
    if args.get(key) != value:
        sys.exit(f"Paramètre PostgreSQL incorrect : {key}")

if args.get("password") != os.environ["SYNAPSE_DB_PASSWORD"]:
    sys.exit("Le mot de passe PostgreSQL de Synapse ne correspond pas à .env.")

print("Configuration PostgreSQL cohérente.")
PY

    info "Configuration existante vérifiée."

fi

# --------------------------------------------------
# 5. Vérification Docker Compose
# --------------------------------------------------

docker compose config -q \
    || error "La configuration Docker Compose est invalide."

info "Configuration Docker Compose valide."

# --------------------------------------------------
# 6. Vérification Synapse
# --------------------------------------------------

info "Vérification de la configuration Synapse."

docker compose run --rm --no-deps \
    --entrypoint python synapse \
    -m synapse.config \
    -c /data/homeserver.yaml \
    || error "La configuration Synapse est invalide."

# --------------------------------------------------
# 7. Démarrage des services
# --------------------------------------------------

info "Démarrage de Kibare."

docker compose up -d --wait --wait-timeout 180 \
    || error "Le démarrage a échoué. Consulte les logs avec : docker compose logs."

# --------------------------------------------------
# 8. Résultat
# --------------------------------------------------

info "État des services :"

docker compose ps

printf '\nKibare est démarré.\n'
printf 'Element Web : http://127.0.0.1:8080\n'
printf 'Matrix API  : http://127.0.0.1:8008\n'
