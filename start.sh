#!/usr/bin/env bash

set -Eeuo pipefail

# Configuration du projet

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

file_checksum() {
    docker run --rm \
        -v "$DATA_DIR:/data:ro" \
        --entrypoint python \
        "$SYNAPSE_IMAGE" \
        -c 'import hashlib; from pathlib import Path; print(hashlib.sha256(Path("/data/homeserver.yaml").read_bytes()).hexdigest())'
}

# 1. Vérification des prérequis

command -v docker >/dev/null 2>&1 \
    || error "Docker n'est pas installé."

command -v openssl >/dev/null 2>&1 \
    || error "OpenSSL est nécessaire."

command -v python3 >/dev/null 2>&1 \
    || error "Python 3 est nécessaire pour préparer la configuration locale."

docker compose version >/dev/null 2>&1 \
    || error "Le plugin Docker Compose est introuvable."

docker info >/dev/null 2>&1 \
    || error "Docker n'est pas accessible."

[ -f compose.yaml ] \
    || error "compose.yaml est introuvable."

[ -f .env.example ] \
    || error ".env.example est introuvable."

info "Prérequis vérifiés."

# 2. Préparation des variables d'environnement

if [ ! -f "$ENV_FILE" ]; then

    info "Première installation : création du fichier .env."

    DB_PASSWORD="$(openssl rand -hex 32)"
    REGISTRATION_SECRET="$(openssl rand -hex 32)"
    KEYCLOAK_ADMIN_PASSWORD="$(openssl rand -hex 32)"
    OIDC_CLIENT_SECRET="$(openssl rand -hex 32)"
    INITIAL_ADMIN_PASSWORD="$(openssl rand -hex 32)"

    (
        umask 077
        printf '# Secrets locaux de Kibare\nSYNAPSE_DB_PASSWORD=%s\nSYNAPSE_REGISTRATION_SHARED_SECRET=%s\nKEYCLOAK_ADMIN_USERNAME=kcadmin\nKEYCLOAK_ADMIN_PASSWORD=%s\nSYNAPSE_OIDC_CLIENT_SECRET=%s\nKIBARE_INITIAL_ADMIN_PASSWORD=%s\n' \
            "$DB_PASSWORD" "$REGISTRATION_SECRET" "$KEYCLOAK_ADMIN_PASSWORD" \
            "$OIDC_CLIENT_SECRET" "$INITIAL_ADMIN_PASSWORD" > "$ENV_FILE"
    )

    info "Secrets locaux générés."

else

    info "Fichier .env existant : conservation."

    DB_PASSWORD="$(
        sed -n 's/^SYNAPSE_DB_PASSWORD=//p' "$ENV_FILE" | head -n 1
    )"

    [ -n "$DB_PASSWORD" ] \
        || error "SYNAPSE_DB_PASSWORD est absent ou vide."

    [[ "$DB_PASSWORD" =~ ^[a-f0-9]{64}$ ]] \
        || error "Le mot de passe doit être une chaîne hexadécimale de 64 caractères. Ne le modifie pas sans adapter également la configuration Synapse et PostgreSQL."

    REGISTRATION_SECRET="$(
        sed -n 's/^SYNAPSE_REGISTRATION_SHARED_SECRET=//p' "$ENV_FILE" | head -n 1
    )"

    if [ -z "$REGISTRATION_SECRET" ]; then
        REGISTRATION_SECRET="$(openssl rand -hex 32)"
        (
            umask 077
            printf '\nSYNAPSE_REGISTRATION_SHARED_SECRET=%s\n' \
                "$REGISTRATION_SECRET" >> "$ENV_FILE"
        )
        info "Secret local d'inscription administrative généré."
    fi

    [[ "$REGISTRATION_SECRET" =~ ^[a-f0-9]{64}$ ]] \
        || error "SYNAPSE_REGISTRATION_SHARED_SECRET doit être une chaîne hexadécimale de 64 caractères."

    read_env_value() {
        sed -n "s/^$1=//p" "$ENV_FILE" | head -n 1
    }

    KEYCLOAK_ADMIN_USERNAME="$(read_env_value KEYCLOAK_ADMIN_USERNAME)"
    if [ -z "$KEYCLOAK_ADMIN_USERNAME" ]; then
        KEYCLOAK_ADMIN_USERNAME="kcadmin"
        printf '\nKEYCLOAK_ADMIN_USERNAME=%s\n' "$KEYCLOAK_ADMIN_USERNAME" >> "$ENV_FILE"
    fi
    [[ "$KEYCLOAK_ADMIN_USERNAME" =~ ^[a-zA-Z0-9._-]{3,32}$ ]] \
        || error "KEYCLOAK_ADMIN_USERNAME doit contenir 3 à 32 lettres, chiffres, points, tirets ou soulignés."

    KEYCLOAK_ADMIN_PASSWORD="$(read_env_value KEYCLOAK_ADMIN_PASSWORD)"
    if [ -z "$KEYCLOAK_ADMIN_PASSWORD" ]; then
        KEYCLOAK_ADMIN_PASSWORD="$(openssl rand -hex 32)"
        printf 'KEYCLOAK_ADMIN_PASSWORD=%s\n' "$KEYCLOAK_ADMIN_PASSWORD" >> "$ENV_FILE"
    fi
    [[ "$KEYCLOAK_ADMIN_PASSWORD" =~ ^[a-f0-9]{64}$ ]] \
        || error "KEYCLOAK_ADMIN_PASSWORD doit être une chaîne hexadécimale de 64 caractères."

    OIDC_CLIENT_SECRET="$(read_env_value SYNAPSE_OIDC_CLIENT_SECRET)"
    if [ -z "$OIDC_CLIENT_SECRET" ]; then
        OIDC_CLIENT_SECRET="$(openssl rand -hex 32)"
        printf 'SYNAPSE_OIDC_CLIENT_SECRET=%s\n' "$OIDC_CLIENT_SECRET" >> "$ENV_FILE"
    fi
    [[ "$OIDC_CLIENT_SECRET" =~ ^[a-f0-9]{64}$ ]] \
        || error "SYNAPSE_OIDC_CLIENT_SECRET doit être une chaîne hexadécimale de 64 caractères."

    INITIAL_ADMIN_PASSWORD="$(read_env_value KIBARE_INITIAL_ADMIN_PASSWORD)"
    if [ -z "$INITIAL_ADMIN_PASSWORD" ]; then
        INITIAL_ADMIN_PASSWORD="$(openssl rand -hex 32)"
        printf 'KIBARE_INITIAL_ADMIN_PASSWORD=%s\n' "$INITIAL_ADMIN_PASSWORD" >> "$ENV_FILE"
    fi
    [[ "$INITIAL_ADMIN_PASSWORD" =~ ^[a-f0-9]{64}$ ]] \
        || error "KIBARE_INITIAL_ADMIN_PASSWORD doit être une chaîne hexadécimale de 64 caractères."

    chmod 600 "$ENV_FILE"

fi

# Keycloak importe le realm une seule fois. Le fichier rendu contient des
# secrets locaux et est ignoré par Git.
IMPORT_DIR="$PROJECT_DIR/keycloak/import"
mkdir -p "$IMPORT_DIR"
KEYCLOAK_ADMIN_USERNAME="${KEYCLOAK_ADMIN_USERNAME:-$(sed -n 's/^KEYCLOAK_ADMIN_USERNAME=//p' "$ENV_FILE" | head -n 1)}"
KEYCLOAK_ADMIN_PASSWORD="${KEYCLOAK_ADMIN_PASSWORD:-$(sed -n 's/^KEYCLOAK_ADMIN_PASSWORD=//p' "$ENV_FILE" | head -n 1)}"
OIDC_CLIENT_SECRET="${OIDC_CLIENT_SECRET:-$(sed -n 's/^SYNAPSE_OIDC_CLIENT_SECRET=//p' "$ENV_FILE" | head -n 1)}"
INITIAL_ADMIN_PASSWORD="${INITIAL_ADMIN_PASSWORD:-$(sed -n 's/^KIBARE_INITIAL_ADMIN_PASSWORD=//p' "$ENV_FILE" | head -n 1)}"

export KEYCLOAK_ADMIN_USERNAME KEYCLOAK_ADMIN_PASSWORD OIDC_CLIENT_SECRET INITIAL_ADMIN_PASSWORD
python3 - "$PROJECT_DIR/keycloak/kibare-realm.json.template" "$IMPORT_DIR/kibare-realm.json" <<'PY'
import json
import os
import sys
from pathlib import Path

template = Path(sys.argv[1]).read_text()
replacements = {
    "__SYNAPSE_OIDC_CLIENT_SECRET__": os.environ["OIDC_CLIENT_SECRET"],
    "__KIBARE_INITIAL_ADMIN_PASSWORD__": os.environ["INITIAL_ADMIN_PASSWORD"],
}
for marker, value in replacements.items():
    template = template.replace(marker, value)
if "__" in template:
    raise SystemExit("Un marqueur secret du realm Keycloak n'a pas été remplacé.")
json.loads(template)
Path(sys.argv[2]).write_text(template)
PY
docker run --rm \
    -v "$IMPORT_DIR:/import" \
    --entrypoint python \
    "$SYNAPSE_IMAGE" \
    -c 'import os; from pathlib import Path; p=Path("/import/kibare-realm.json"); os.chown(p, 1000, 0); p.chmod(0o640); os.chown(p.parent, 1000, 0); p.parent.chmod(0o750)'

unset INITIAL_ADMIN_PASSWORD

# 3. Préparation des données Synapse

mkdir -p "$DATA_DIR"

CONFIG_HASH_BEFORE=""
if [ -f "$CONFIG_FILE" ]; then
    CONFIG_HASH_BEFORE="$(file_checksum)"
fi

if [ -f "$CONFIG_FILE" ] && [ ! -f "$SIGNING_KEY" ]; then
    error "homeserver.yaml existe, mais la clé de signature est absente. Intervention manuelle nécessaire."
fi

if [ ! -f "$CONFIG_FILE" ] && [ -f "$SIGNING_KEY" ]; then
    error "Une clé de signature existe sans homeserver.yaml. Intervention manuelle nécessaire."
fi

# 4. Initialisation de Synapse

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

    # Configuration PostgreSQL et souveraineté avec PyYAML.
    docker run --rm -i \
        -v "$DATA_DIR:/data" \
        -e SYNAPSE_DB_PASSWORD="$DB_PASSWORD" \
        -e SYNAPSE_REGISTRATION_SHARED_SECRET="$REGISTRATION_SECRET" \
        -e SYNAPSE_SERVER_NAME="$SERVER_NAME" \
        -e SYNAPSE_OIDC_CLIENT_SECRET="$OIDC_CLIENT_SECRET" \
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
config["registration_shared_secret"] = os.environ[
    "SYNAPSE_REGISTRATION_SHARED_SECRET"
]
config["enable_registration"] = False
config["enable_registration_without_verification"] = False
config["allow_guest_access"] = False
config["report_stats"] = False
config["federation_domain_whitelist"] = []
config["trusted_key_servers"] = []
config["suppress_key_server_warning"] = True
config["public_baseurl"] = "http://127.0.0.1:8008/"
config["enable_registration"] = False
config["password_config"] = {"enabled": False}
config["oidc_providers"] = [
    {
        "idp_id": "kibare",
        "idp_name": "Kibare",
        "discover": False,
        "skip_verification": True,
        "issuer": "http://127.0.0.1:8082/realms/kibare",
        "client_id": "kibare-synapse",
        "client_secret": os.environ["SYNAPSE_OIDC_CLIENT_SECRET"],
        "authorization_endpoint": "http://127.0.0.1:8082/realms/kibare/protocol/openid-connect/auth",
        "token_endpoint": "http://keycloak:8080/realms/kibare/protocol/openid-connect/token",
        "userinfo_endpoint": "http://keycloak:8080/realms/kibare/protocol/openid-connect/userinfo",
        "jwks_uri": "http://keycloak:8080/realms/kibare/protocol/openid-connect/certs",
        "scopes": ["openid", "profile", "email"],
        "allow_existing_users": True,
        "enable_registration": False,
        "user_profile_method": "userinfo_endpoint",
        "backchannel_logout_enabled": True,
        "user_mapping_provider": {
            "config": {
                "localpart_template": "{{ user.preferred_username }}",
                "display_name_template": "{{ user.name }}",
            }
        },
    }
]
config["sso"] = {
    "client_whitelist": [
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8766/callback",
    ]
}

for listener in config.get("listeners", []):
    resources = listener.get("resources", [])
    for resource in resources:
        resource["names"] = [
            name for name in resource.get("names", []) if name != "federation"
        ]
    listener["resources"] = [
        resource for resource in resources if resource.get("names")
    ]

temporary_path = path.with_suffix(".yaml.tmp")
temporary_path.write_text(
    yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
)
os.chown(temporary_path, 991, 991)
temporary_path.chmod(0o640)
temporary_path.replace(path)

data_dir = Path("/data")
os.chown(data_dir, -1, 991)
os.chmod(data_dir, data_dir.stat().st_mode & 0o777 | 0o070)
signing_key = data_dir / f"{os.environ['SYNAPSE_SERVER_NAME']}.signing.key"
os.chown(signing_key, 991, 991)
signing_key.chmod(0o640)
PY

    info "Configuration PostgreSQL et politiques de sécurité appliquées."

else

    info "Configuration Synapse existante : vérification et application des politiques locales."

    # Vérifier que le mot de passe de la configuration correspond
    # à celui du fichier .env, sans afficher le secret.
    docker run --rm -i \
        -v "$DATA_DIR:/data" \
        -e SYNAPSE_DB_PASSWORD="$DB_PASSWORD" \
        -e SYNAPSE_REGISTRATION_SHARED_SECRET="$REGISTRATION_SECRET" \
        -e SYNAPSE_SERVER_NAME="$SERVER_NAME" \
        -e SYNAPSE_OIDC_CLIENT_SECRET="$OIDC_CLIENT_SECRET" \
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

config["registration_shared_secret"] = os.environ[
    "SYNAPSE_REGISTRATION_SHARED_SECRET"
]
config["enable_registration"] = False
config["enable_registration_without_verification"] = False
config["allow_guest_access"] = False
config["report_stats"] = False
config["federation_domain_whitelist"] = []
config["trusted_key_servers"] = []
config["suppress_key_server_warning"] = True
config["public_baseurl"] = "http://127.0.0.1:8008/"
config["enable_registration"] = False
config["password_config"] = {"enabled": False}
config["oidc_providers"] = [
    {
        "idp_id": "kibare",
        "idp_name": "Kibare",
        "discover": False,
        "skip_verification": True,
        "issuer": "http://127.0.0.1:8082/realms/kibare",
        "client_id": "kibare-synapse",
        "client_secret": os.environ["SYNAPSE_OIDC_CLIENT_SECRET"],
        "authorization_endpoint": "http://127.0.0.1:8082/realms/kibare/protocol/openid-connect/auth",
        "token_endpoint": "http://keycloak:8080/realms/kibare/protocol/openid-connect/token",
        "userinfo_endpoint": "http://keycloak:8080/realms/kibare/protocol/openid-connect/userinfo",
        "jwks_uri": "http://keycloak:8080/realms/kibare/protocol/openid-connect/certs",
        "scopes": ["openid", "profile", "email"],
        "allow_existing_users": True,
        "enable_registration": False,
        "user_profile_method": "userinfo_endpoint",
        "backchannel_logout_enabled": True,
        "user_mapping_provider": {
            "config": {
                "localpart_template": "{{ user.preferred_username }}",
                "display_name_template": "{{ user.name }}",
            }
        },
    }
]
config["sso"] = {
    "client_whitelist": [
        "http://127.0.0.1:8080",
        "http://127.0.0.1:8080/",
        "http://localhost:8080",
        "http://localhost:8080/",
        "http://127.0.0.1:8081",
        "http://127.0.0.1:8081/",
        "http://localhost:8081",
        "http://localhost:8081/",
        "http://kibare.test",
        "http://kibare.test/",
        "https://kibare.test",
        "https://kibare.test/",
        "http://127.0.0.1:8766/callback",
    ]
}

for listener in config.get("listeners", []):
    resources = listener.get("resources", [])
    for resource in resources:
        resource["names"] = [
            name for name in resource.get("names", []) if name != "federation"
        ]
    listener["resources"] = [
        resource for resource in resources if resource.get("names")
    ]

path = Path("/data/homeserver.yaml")
temporary_path = path.with_suffix(".yaml.tmp")
temporary_path.write_text(
    yaml.safe_dump(config, sort_keys=False, allow_unicode=True)
)
os.chown(temporary_path, 991, 991)
temporary_path.chmod(0o640)
temporary_path.replace(path)

data_dir = Path("/data")
os.chown(data_dir, -1, 991)
os.chmod(data_dir, data_dir.stat().st_mode & 0o777 | 0o070)
signing_key = data_dir / f"{os.environ['SYNAPSE_SERVER_NAME']}.signing.key"
os.chown(signing_key, 991, 991)
signing_key.chmod(0o640)

print("Configuration PostgreSQL cohérente.")
PY

    info "Configuration existante vérifiée."

fi

unset OIDC_CLIENT_SECRET
CONFIG_HASH_AFTER="$(file_checksum)"

# 5. Vérification Docker Compose

docker compose config -q \
    || error "La configuration Docker Compose est invalide."

info "Configuration Docker Compose valide."

# 6. Vérification Synapse

info "Vérification de la configuration Synapse."

docker compose run --rm --no-deps \
    --entrypoint python synapse \
    -m synapse.config \
    -c /data/homeserver.yaml \
    || error "La configuration Synapse est invalide."

# 7. Démarrage des services

info "Démarrage de Kibare."

docker compose up -d --wait --wait-timeout 180 \
    || error "Le démarrage a échoué. Consulte les logs avec : docker compose logs."

if [ -n "$CONFIG_HASH_BEFORE" ] && [ "$CONFIG_HASH_BEFORE" != "$CONFIG_HASH_AFTER" ]; then
    info "Configuration Synapse modifiée : redémarrage du service pour appliquer les changements."
    docker compose restart synapse \
        || error "Le redémarrage de Synapse a échoué."
    docker compose up -d --wait --wait-timeout 180 \
        || error "Synapse n'est pas redevenu sain. Consulte les logs avec : docker compose logs synapse."
fi

# 8. Provisionnement du compte administrateur Synapse

info "Provisionnement du compte administrateur Synapse (idempotent)."

INITIAL_ADMIN_PASSWORD="$(sed -n 's/^KIBARE_INITIAL_ADMIN_PASSWORD=//p' "$ENV_FILE" | head -n 1)"

if [ -z "$INITIAL_ADMIN_PASSWORD" ]; then
    error "KIBARE_INITIAL_ADMIN_PASSWORD est absent du fichier .env."
fi

docker compose exec -T synapse \
    register_new_matrix_user \
    -u admin \
    -p "$INITIAL_ADMIN_PASSWORD" \
    --admin \
    --exists-ok \
    -c /data/homeserver.yaml \
    || error "Le provisionnement du compte admin Synapse a échoué."

unset INITIAL_ADMIN_PASSWORD

info "Compte @admin:kibare.test prêt (créé ou déjà présent)."

# 9. Résultat

info "État des services :"

docker compose ps

printf '\nKibare est démarré.\n'
printf 'Element Web    : http://127.0.0.1:8080\n'
printf 'Matrix API     : http://127.0.0.1:8008\n'
printf 'Portail        : http://127.0.0.1:8081\n'
printf 'Administration : http://127.0.0.1:8081/admin.html\n'
