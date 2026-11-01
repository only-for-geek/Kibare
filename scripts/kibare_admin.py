#!/usr/bin/env python3
"""Administrative workflows for a locally hosted Kibare Matrix server."""

import argparse
import copy
import getpass
import http.server
import json
import os
import re
import sys
import time
import webbrowser
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, quote, urlencode, urlsplit
from urllib.request import Request, urlopen


DEFAULT_HOMESERVER = "http://127.0.0.1:8008"
DEFAULT_IDENTITY_URL = "http://127.0.0.1:8082"
DEFAULT_SERVER_NAME = "kibare.test"
ADMIN_LOGIN_CALLBACK = "http://127.0.0.1:8766/callback"
USERNAME_PATTERN = re.compile(r"^[a-z0-9._=-]{1,255}$")
ROOM_ROLE_LEVELS = {"member": 0, "moderator": 50}


class AdminError(Exception):
    """An expected error returned by the local Matrix server."""

    def __init__(self, message, status_code=None):
        super().__init__(message)
        self.status_code = status_code


class SynapseClient:
    def __init__(self, base_url, access_token=None):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise AdminError("L'URL du homeserver doit commencer par http:// ou https://.")
        if parsed.username or parsed.password:
            raise AdminError("Ne placez pas d'identifiants dans l'URL du homeserver.")
        if access_token and any(char in access_token for char in "\r\n"):
            raise AdminError(
                "Le jeton Matrix contient plusieurs lignes. Relancez la commande login."
            )
        self.base_url = base_url.rstrip("/")
        self.access_token = access_token

    def request(self, method, path, payload=None):
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        request = Request(
            self.base_url + path,
            data=body,
            headers=headers,
            method=method,
        )
        try:
            with urlopen(request, timeout=15) as response:
                raw_body = response.read()
        except HTTPError as error:
            try:
                detail = json.loads(error.read()).get("error")
            except (json.JSONDecodeError, AttributeError):
                detail = None
            message = detail or f"Le homeserver a répondu avec le statut HTTP {error.code}."
            raise AdminError(message, status_code=error.code) from error
        except URLError as error:
            raise AdminError(f"Impossible de joindre le homeserver : {error.reason}") from error

        if not raw_body:
            return {}
        try:
            return json.loads(raw_body)
        except json.JSONDecodeError as error:
            raise AdminError("Le homeserver a renvoyé une réponse JSON invalide.") from error


class KeycloakClient:
    def __init__(self, base_url, username, password):
        parsed = urlsplit(base_url)
        if parsed.scheme not in ("http", "https") or not parsed.netloc:
            raise AdminError("L'URL Keycloak doit commencer par http:// ou https://.")
        if parsed.username or parsed.password:
            raise AdminError("Ne placez pas d'identifiants dans l'URL Keycloak.")
        self.base_url = base_url.rstrip("/")
        self.username = username
        self.password = password
        self.access_token = None

    def _request(self, method, path, payload=None):
        headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            headers["Content-Type"] = "application/json"
            body = json.dumps(payload).encode("utf-8")
        if self.access_token:
            headers["Authorization"] = f"Bearer {self.access_token}"

        request = Request(self.base_url + path, data=body, headers=headers, method=method)
        try:
            with urlopen(request, timeout=15) as response:
                raw_body = response.read()
                location = response.headers.get("Location")
        except HTTPError as error:
            try:
                detail = json.loads(error.read()).get("errorMessage")
            except (json.JSONDecodeError, AttributeError):
                detail = None
            message = detail or f"Keycloak a répondu avec le statut HTTP {error.code}."
            raise AdminError(message, status_code=error.code) from error
        except URLError as error:
            raise AdminError(f"Impossible de joindre Keycloak : {error.reason}") from error

        if not raw_body:
            return {}, location
        try:
            return json.loads(raw_body), location
        except json.JSONDecodeError as error:
            raise AdminError("Keycloak a renvoyé une réponse JSON invalide.") from error

    def authenticate_admin(self):
        try:
            with urlopen(
                Request(
                    f"{self.base_url}/realms/master/protocol/openid-connect/token",
                    data=urlencode(
                        {
                            "client_id": "admin-cli",
                            "grant_type": "password",
                            "username": self.username,
                            "password": self.password,
                        }
                    ).encode("utf-8"),
                    headers={"Content-Type": "application/x-www-form-urlencoded"},
                    method="POST",
                ),
                timeout=15,
            ) as response:
                result = json.loads(response.read())
        except HTTPError as error:
            raise AdminError(
                "Authentification de l'administrateur Keycloak refusée.",
                status_code=error.code,
            ) from error
        except URLError as error:
            raise AdminError(f"Impossible de joindre Keycloak : {error.reason}") from error
        except json.JSONDecodeError as error:
            raise AdminError("Keycloak a renvoyé une réponse JSON invalide.") from error

        self.access_token = result.get("access_token")
        if not self.access_token:
            raise AdminError("Keycloak n'a pas fourni de jeton d'administration.")

    def find_user(self, username):
        path = "/admin/realms/kibare/users?" + urlencode(
            {"username": username, "exact": "true"}
        )
        users, _ = self._request("GET", path)
        return next((user for user in users if user.get("username") == username), None)

    def create_user(self, username, display_name, password):
        self.authenticate_admin()
        if self.find_user(username):
            raise AdminError(
                f"L'identité Keycloak {username} existe déjà ; aucun changement n'a été appliqué."
            )

        first_name, _, last_name = display_name.partition(" ")
        self._request(
            "POST",
            "/admin/realms/kibare/users",
            {
                "username": username,
                "enabled": True,
                "emailVerified": True,
                "firstName": first_name,
                "lastName": last_name,
                "requiredActions": [],
                "credentials": [
                    {
                        "type": "password",
                        "value": password,
                        "temporary": True,
                    }
                ],
            },
        )
        user = self.find_user(username)
        if not user or not user.get("id"):
            raise AdminError("Le compte Keycloak a été créé sans identifiant récupérable.")
        return user["id"]

    def delete_user(self, user_id):
        self._request("DELETE", f"/admin/realms/kibare/users/{quote(user_id, safe='')}")

    def deactivate_user(self, username):
        self.authenticate_admin()
        user = self.find_user(username)
        if not user:
            return
        user["enabled"] = False
        user_id = quote(user["id"], safe="")
        self._request("PUT", f"/admin/realms/kibare/users/{user_id}", user)
        self._request("POST", f"/admin/realms/kibare/users/{user_id}/logout")


class LoginCallbackHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlsplit(self.path)
        if parsed.path != "/callback":
            self.send_error(404)
            return
        params = parse_qs(parsed.query)
        token = params.get("loginToken", [None])[0]
        error = params.get("error", [None])[0]
        if token:
            self.server.login_token = token
            message = "Connexion validée. Vous pouvez fermer cette fenêtre."
            status = 200
        elif error:
            self.server.login_error = "La connexion SSO a été refusée."
            message = self.server.login_error
            status = 400
        else:
            self.server.login_error = "Réponse SSO invalide."
            message = self.server.login_error
            status = 400
        body = (
            "<!doctype html><html lang=\"fr\"><meta charset=\"utf-8\">"
            "<title>Kibare : Connexion</title>"
            "<p>" + message + "</p></html>"
        ).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, _format, *_args):
        return


def local_env_value(name):
    if name in os.environ:
        return os.environ[name]
    try:
        with open(".env", encoding="utf-8") as env_file:
            for line in env_file:
                key, separator, value = line.strip().partition("=")
                if separator and key == name:
                    return value
    except OSError:
        pass
    return ""


def matrix_user_id(value, server_name):
    localpart = value
    if value.startswith("@"):
        parts = value[1:].split(":", 1)
        if len(parts) != 2 or parts[1] != server_name:
            raise AdminError(f"Seuls les comptes du serveur {server_name} sont autorisés.")
        localpart = parts[0]
    if not USERNAME_PATTERN.fullmatch(localpart):
        raise AdminError("Identifiant invalide : utilisez des lettres minuscules, chiffres, '.', '_' ou '-'.")
    return f"@{localpart}:{server_name}"


def validate_existing_user_id(value, server_name):
    if not value.startswith("@") or ":" not in value:
        raise AdminError("L'identifiant doit être complet, par exemple @agent:kibare.test.")
    localpart, supplied_server = value[1:].split(":", 1)
    if supplied_server != server_name:
        raise AdminError(f"Seuls les comptes du serveur {server_name} sont autorisés.")
    return matrix_user_id(localpart, server_name)


def room_payload(name, invitees):
    return {
        "name": name,
        "preset": "private_chat",
        "visibility": "private",
        "creation_content": {"m.federate": False},
        "initial_state": [
            {
                "type": "m.room.encryption",
                "state_key": "",
                "content": {"algorithm": "m.megolm.v1.aes-sha2"},
            },
            {
                "type": "m.room.history_visibility",
                "state_key": "",
                "content": {"history_visibility": "joined"},
            },
        ],
        "invite": invitees,
    }


def room_role_payload(current_power_levels, user_id, role):
    if role not in ROOM_ROLE_LEVELS:
        raise AdminError("Le rôle doit être 'member' ou 'moderator'.")
    updated = copy.deepcopy(current_power_levels)
    users = updated.setdefault("users", {})
    users[user_id] = ROOM_ROLE_LEVELS[role]
    return updated


def validate_room_id(value, server_name):
    if not value.startswith("!") or ":" not in value:
        raise AdminError("L'identifiant doit être un identifiant de salon Matrix commençant par !.")
    if value.rsplit(":", 1)[1] != server_name:
        raise AdminError(f"Seuls les salons du serveur {server_name} sont autorisés.")
    return value


def admin_client(args):
    token = os.environ.get("KIBARE_ADMIN_TOKEN")
    if not token:
        raise AdminError(
            "KIBARE_ADMIN_TOKEN est absent. Connectez-vous avec la commande login "
            "et conservez le jeton uniquement dans votre environnement local."
        )
    return SynapseClient(args.homeserver, token)


def open_browser_without_stdout(url):
    sys.stdout.flush()
    stdout_fd = os.dup(sys.stdout.fileno())
    try:
        os.dup2(sys.stderr.fileno(), sys.stdout.fileno())
        webbrowser.open(url)
    finally:
        os.dup2(stdout_fd, sys.stdout.fileno())
        os.close(stdout_fd)


def login(args):
    matrix_user_id(args.username, args.server_name)
    callback_server = http.server.HTTPServer(
        ("127.0.0.1", 8766),
        LoginCallbackHandler,
    )
    callback_server.timeout = 1
    query = urlencode({"redirectUrl": ADMIN_LOGIN_CALLBACK})
    login_url = (
        f"{args.homeserver.rstrip('/')}/_matrix/client/v3/login/sso/redirect?{query}"
    )
    print(
        "Un navigateur va s'ouvrir pour la connexion Kibare.",
        file=sys.stderr,
    )
    print(f"Si nécessaire, ouvrez : {login_url}", file=sys.stderr)
    open_browser_without_stdout(login_url)
    deadline = time.monotonic() + 300
    try:
        while not getattr(callback_server, "login_token", None):
            if getattr(callback_server, "login_error", None):
                raise AdminError(callback_server.login_error)
            if time.monotonic() >= deadline:
                raise AdminError("Délai de connexion SSO dépassé (5 minutes).")
            callback_server.handle_request()
    finally:
        callback_server.server_close()

    client = SynapseClient(args.homeserver)
    result = client.request(
        "POST",
        "/_matrix/client/v3/login",
        {
            "type": "m.login.token",
            "token": callback_server.login_token,
            "device_id": "KIBARE-CLI",
            "initial_device_display_name": "Kibare CLI",
        },
    )
    access_token = result.get("access_token")
    if not access_token:
        raise AdminError("Le homeserver n'a pas fourni de jeton de session.")
    print(access_token)


def enroll(args):
    user_id = matrix_user_id(args.username, args.server_name)
    client = admin_client(args)
    user_path = f"/_synapse/admin/v2/users/{quote(user_id, safe='')}"
    matrix_user_exists = False
    try:
        matrix_user = client.request("GET", user_path)
    except AdminError as error:
        if error.status_code != 404:
            raise
    else:
        matrix_user_exists = True
        if matrix_user.get("deactivated"):
            raise AdminError(
                f"Le compte Matrix {user_id} est désactivé. Il n'a pas été réactivé ; "
                "utilisez un autre identifiant ou demandez explicitement sa réactivation."
            )

    password = getpass.getpass(f"Nouveau mot de passe temporaire pour {user_id} : ")
    if len(password) < 14:
        raise AdminError("Le mot de passe doit contenir au moins 14 caractères.")
    confirmation = getpass.getpass("Confirmer le mot de passe : ")
    if password != confirmation:
        raise AdminError("Les mots de passe ne correspondent pas.")

    idp_admin_password = local_env_value("KEYCLOAK_ADMIN_PASSWORD")
    if not idp_admin_password:
        raise AdminError("KEYCLOAK_ADMIN_PASSWORD est absent du .env local.")
    keycloak = KeycloakClient(
        args.identity_url,
        local_env_value("KEYCLOAK_ADMIN_USERNAME") or "kcadmin",
        idp_admin_password,
    )
    keycloak_user_id = keycloak.create_user(
        args.username,
        args.display_name,
        password,
    )

    if not matrix_user_exists:
        try:
            client.request(
                "PUT",
                user_path,
                {
                    "admin": False,
                    "displayname": args.display_name,
                    "deactivated": False,
                },
            )
        except AdminError as error:
            try:
                keycloak.delete_user(keycloak_user_id)
            except AdminError as cleanup_error:
                raise AdminError(
                    f"Création Matrix impossible ({error}); la suppression compensatoire "
                    f"Keycloak a aussi échoué ({cleanup_error})."
                ) from error
            raise
    print(f"Compte enrôlé : {user_id}")
    print("L'agent devra définir son mot de passe lors de sa première connexion (configuration TOTP optionnelle).")


def revoke(args):
    user_id = validate_existing_user_id(args.user_id, args.server_name)
    client = admin_client(args)
    client.request(
        "POST",
        f"/_synapse/admin/v1/deactivate/{quote(user_id, safe='')}",
        {"erase": False},
    )
    idp_admin_password = local_env_value("KEYCLOAK_ADMIN_PASSWORD")
    if not idp_admin_password:
        raise AdminError(
            "Le compte Matrix est révoqué, mais KEYCLOAK_ADMIN_PASSWORD est absent ; "
            "la session du fournisseur d'identité n'a pas pu être révoquée."
        )
    keycloak = KeycloakClient(
        args.identity_url,
        local_env_value("KEYCLOAK_ADMIN_USERNAME") or "kcadmin",
        idp_admin_password,
    )
    keycloak.deactivate_user(user_id[1:].split(":", 1)[0])
    print(f"Compte désactivé et sessions révoquées : {user_id}")


def create_room(args):
    invitees = [
        validate_existing_user_id(user_id, args.server_name)
        for user_id in args.invite
    ]
    client = admin_client(args)
    result = client.request(
        "POST",
        "/_matrix/client/v3/createRoom",
        room_payload(args.name, invitees),
    )
    room_id = result.get("room_id")
    if not room_id:
        raise AdminError("Le homeserver n'a pas renvoyé l'identifiant du salon.")
    print(f"Salon institutionnel créé : {room_id}")


def set_room_role(args):
    user_id = validate_existing_user_id(args.user_id, args.server_name)
    room_id = validate_room_id(args.room_id, args.server_name)
    client = admin_client(args)
    encoded_room_id = quote(room_id, safe="")
    state_path = (
        f"/_matrix/client/v3/rooms/{encoded_room_id}"
        "/state/m.room.power_levels/"
    )
    current = client.request("GET", state_path)
    updated = room_role_payload(current, user_id, args.role)
    client.request("PUT", state_path, updated)
    print(f"Rôle {args.role} défini pour {user_id} dans {room_id}")


def build_parser():
    parser = argparse.ArgumentParser(
        description="Gestion locale des comptes et salons Kibare."
    )
    parser.add_argument("--homeserver", default=DEFAULT_HOMESERVER)
    parser.add_argument("--identity-url", default=DEFAULT_IDENTITY_URL)
    parser.add_argument("--server-name", default=DEFAULT_SERVER_NAME)
    commands = parser.add_subparsers(dest="command", required=True)

    login_parser = commands.add_parser(
        "login", help="Obtenir un jeton administrateur sans afficher le mot de passe."
    )
    login_parser.add_argument("username", help="Nom d'utilisateur administrateur")
    login_parser.set_defaults(handler=login)

    enroll_parser = commands.add_parser(
        "enroll", help="Créer un compte agent non-administrateur."
    )
    enroll_parser.add_argument("username")
    enroll_parser.add_argument("--display-name", required=True)
    enroll_parser.set_defaults(handler=enroll)

    revoke_parser = commands.add_parser(
        "revoke", help="Désactiver un compte et révoquer ses sessions."
    )
    revoke_parser.add_argument("user_id")
    revoke_parser.set_defaults(handler=revoke)

    room_parser = commands.add_parser(
        "create-room", help="Créer un salon privé, chiffré et non fédéré."
    )
    room_parser.add_argument("--name", required=True)
    room_parser.add_argument("--invite", action="append", default=[], metavar="@AGENT:SERVEUR")
    room_parser.set_defaults(handler=create_room)

    role_parser = commands.add_parser(
        "set-room-role",
        help="Attribuer le rôle membre ou modérateur dans un salon local.",
    )
    role_parser.add_argument("room_id", help="Identifiant de salon commençant par !")
    role_parser.add_argument("user_id")
    role_parser.add_argument("role", choices=sorted(ROOM_ROLE_LEVELS))
    role_parser.set_defaults(handler=set_room_role)
    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    try:
        args.handler(args)
    except AdminError as error:
        print(f"Erreur : {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
