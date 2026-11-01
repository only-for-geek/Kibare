#!/usr/bin/env python3
"""Kibare Admin API : backend interne léger.

Ce serveur HTTP tourne exclusivement sur le réseau Docker interne.
Il n'est jamais exposé directement à l'extérieur ; seul nginx (portal)
y accède via un proxy sur /api/.

Variables d'environnement attendues (injectées par Docker Compose) :
  SYNAPSE_BASE_URL                    : ex. http://synapse:8008
  SYNAPSE_REGISTRATION_SHARED_SECRET  : clé partagée du homeserver.yaml
  KEYCLOAK_BASE_URL                   : ex. http://keycloak:8080
  KEYCLOAK_ADMIN_USERNAME             : identifiant de l'admin Keycloak
  KEYCLOAK_ADMIN_PASSWORD             : mot de passe de l'admin Keycloak
  SERVER_NAME                         : domaine Matrix (ex. kibare.test)
"""

import hashlib
import hmac
import http.server
import json
import os
import re
import threading
import uuid
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen

# Configuration depuis l'environnement

SYNAPSE_URL = os.environ.get("SYNAPSE_BASE_URL", "http://synapse:8008")
REG_SECRET = os.environ.get("SYNAPSE_REGISTRATION_SHARED_SECRET", "")
KEYCLOAK_URL = os.environ.get("KEYCLOAK_BASE_URL", "http://keycloak:8080")
KC_ADMIN_USER = os.environ.get("KEYCLOAK_ADMIN_USERNAME", "kcadmin")
KC_ADMIN_PASS = os.environ.get("KEYCLOAK_ADMIN_PASSWORD", "")
SERVER_NAME = os.environ.get("SERVER_NAME", "kibare.test")
LISTEN_PORT = int(os.environ.get("ADMIN_API_PORT", "8000"))

USERNAME_RE = re.compile(r"^[a-z0-9._=-]{1,64}$")

# User technique interne : masqué dans l'interface
_TECH_USER = "kibare_internal_api"

# Verrous
_kc_lock = threading.Lock()
_kc_token: str | None = None
_synapse_token_cache: str | None = None
_synapse_token_lock = threading.Lock()


# Helpers HTTP bas niveau (stdlib uniquement)

class APIError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def _json_request(method: str, url: str, payload=None, headers: dict | None = None) -> dict:
    hdrs = {"Accept": "application/json"}
    if headers:
        hdrs.update(headers)
    body = None
    if payload is not None:
        hdrs["Content-Type"] = "application/json"
        body = json.dumps(payload).encode("utf-8")
    req = Request(url, data=body, headers=hdrs, method=method)
    try:
        with urlopen(req, timeout=15) as resp:
            raw = resp.read()
        return json.loads(raw) if raw else {}
    except HTTPError as exc:
        try:
            detail = json.loads(exc.read())
            msg = detail.get("error") or detail.get("errorMessage") or str(exc)
        except Exception:
            msg = str(exc)
        raise APIError(msg, exc.code) from exc
    except URLError as exc:
        raise APIError(f"Connexion impossible : {exc.reason}", 503) from exc


# Keycloak

def _kc_authenticate() -> str:
    global _kc_token
    data = urlencode({
        "client_id": "admin-cli",
        "grant_type": "password",
        "username": KC_ADMIN_USER,
        "password": KC_ADMIN_PASS,
    }).encode("utf-8")
    req = Request(
        f"{KEYCLOAK_URL}/realms/master/protocol/openid-connect/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    try:
        with urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read())
    except (HTTPError, URLError) as exc:
        raise APIError(f"Authentification Keycloak échouée : {exc}", 503) from exc
    token = result.get("access_token")
    if not token:
        raise APIError("Keycloak n'a pas fourni de jeton.", 503)
    _kc_token = token
    return token


def _kc_token_header() -> dict:
    with _kc_lock:
        token = _kc_token or _kc_authenticate()
    return {"Authorization": f"Bearer {token}"}


def _kc_call(method: str, path: str, payload=None, retry: bool = True):
    headers = _kc_token_header()
    try:
        return _json_request(method, f"{KEYCLOAK_URL}{path}", payload, headers)
    except APIError as exc:
        if exc.status == 401 and retry:
            with _kc_lock:
                _kc_authenticate()
            return _kc_call(method, path, payload, retry=False)
        raise


def kc_find_user(username: str):
    path = "/admin/realms/kibare/users?" + urlencode({"username": username, "exact": "true"})
    users = _kc_call("GET", path)
    return next((u for u in users if u.get("username") == username), None)


def kc_list_users() -> list:
    return _kc_call("GET", "/admin/realms/kibare/users?max=200")


def kc_create_user(username: str, display_name: str, password: str, require_totp: bool = False) -> str:
    first, _, last = display_name.partition(" ")
    required_actions = ["UPDATE_PASSWORD"]
    if require_totp:
        required_actions.append("CONFIGURE_TOTP")
    _kc_call("POST", "/admin/realms/kibare/users", {
        "username": username,
        "enabled": True,
        "emailVerified": True,
        "firstName": first,
        "lastName": last or first,
        "requiredActions": required_actions,
        "credentials": [{"type": "password", "value": password, "temporary": True}],
    })
    user = kc_find_user(username)
    if not user or not user.get("id"):
        raise APIError("Compte Keycloak créé sans identifiant récupérable.", 500)
    return user["id"]


def kc_toggle_totp(username: str, require_totp: bool) -> None:
    user = kc_find_user(username)
    if not user:
        raise APIError(f"Utilisateur Keycloak « {username} » introuvable.", 404)
    uid = quote(user["id"], safe="")
    actions = list(user.get("requiredActions") or [])
    if require_totp:
        if "CONFIGURE_TOTP" not in actions:
            actions.append("CONFIGURE_TOTP")
    else:
        actions = [a for a in actions if a != "CONFIGURE_TOTP"]
    user_payload = dict(user)
    user_payload["requiredActions"] = actions
    _kc_call("PUT", f"/admin/realms/kibare/users/{uid}", user_payload)


def kc_deactivate_user(username: str) -> None:
    user = kc_find_user(username)
    if not user:
        return
    uid = quote(user["id"], safe="")
    user_payload = dict(user)
    user_payload["enabled"] = False
    _kc_call("PUT", f"/admin/realms/kibare/users/{uid}", user_payload)
    try:
        _kc_call("POST", f"/admin/realms/kibare/users/{uid}/logout")
    except APIError:
        pass


def kc_delete_user(user_id: str) -> None:
    _kc_call("DELETE", f"/admin/realms/kibare/users/{quote(user_id, safe='')}")


# Synapse (shared secret nonce-MAC pour token admin interne)

def _get_synapse_admin_token() -> str:
    """Retourne (en créant un compte admin dédié si besoin) le token Synapse interne."""
    global _synapse_token_cache
    with _synapse_token_lock:
        if _synapse_token_cache:
            return _synapse_token_cache

        if not REG_SECRET:
            raise APIError("SYNAPSE_REGISTRATION_SHARED_SECRET manquant.", 500)

        for _ in range(3):
            tech_user = f"sys_api_{uuid.uuid4().hex[:8]}"
            nonce_data = _json_request("GET", f"{SYNAPSE_URL}/_synapse/admin/v1/register")
            nonce = nonce_data.get("nonce", "")
            password = "INTERNAL_API_ONLY"

            mac = hmac.new(REG_SECRET.encode("utf-8"), digestmod=hashlib.sha1)
            mac.update(nonce.encode("utf-8"))
            mac.update(b"\x00")
            mac.update(tech_user.encode("utf-8"))
            mac.update(b"\x00")
            mac.update(password.encode("utf-8"))
            mac.update(b"\x00")
            mac.update(b"admin")

            try:
                result = _json_request("POST", f"{SYNAPSE_URL}/_synapse/admin/v1/register", {
                    "nonce": nonce,
                    "username": tech_user,
                    "password": password,
                    "admin": True,
                    "mac": mac.hexdigest(),
                })
                token = result.get("access_token")
                if token:
                    _synapse_token_cache = token
                    return token
            except APIError:
                continue

        raise APIError("Impossible d'obtenir un jeton d'administration Synapse.", 500)


def synapse_admin(method: str, path: str, payload=None) -> dict:
    token = _get_synapse_admin_token()
    return _json_request(
        method,
        f"{SYNAPSE_URL}{path}",
        payload,
        {"Authorization": f"Bearer {token}"},
    )


def synapse_list_users() -> list:
    result = synapse_admin("GET", "/_synapse/admin/v2/users?limit=200&deactivated=false")
    return result.get("users", [])


def synapse_create_user(username: str, display_name: str) -> None:
    user_id = f"@{username}:{SERVER_NAME}"
    synapse_admin("PUT", f"/_synapse/admin/v2/users/{quote(user_id, safe='')}", {
        "admin": False,
        "displayname": display_name,
        "deactivated": False,
    })


def synapse_deactivate_user(username: str) -> None:
    user_id = f"@{username}:{SERVER_NAME}"
    synapse_admin(
        "POST",
        f"/_synapse/admin/v1/deactivate/{quote(user_id, safe='')}",
        {"erase": False},
    )


def synapse_user_exists(username: str) -> bool:
    """Vérifie si un compte Synapse existe (actif ou désactivé)."""
    user_id = f"@{username}:{SERVER_NAME}"
    try:
        result = synapse_admin("GET", f"/_synapse/admin/v2/users/{quote(user_id, safe='')}")
        return bool(result.get("name"))
    except APIError:
        return False


# Handlers HTTP

CORS_HEADERS = {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
}


class AdminAPIHandler(http.server.BaseHTTPRequestHandler):
    server_version = "KibareAdminAPI/1.0"

    def log_message(self, _fmt, *_args):
        pass  # silence logs verbeux

    def _send_json(self, status: int, data: dict) -> None:
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        for k, v in CORS_HEADERS.items():
            self.send_header(k, v)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def _read_json(self) -> dict:
        length = int(self.headers.get("Content-Length", 0))
        if length == 0:
            return {}
        raw = self.rfile.read(length)
        try:
            return json.loads(raw)
        except json.JSONDecodeError as exc:
            raise APIError("Corps JSON invalide.", 400) from exc

    def _route(self, method: str) -> None:
        path = self.path.split("?")[0]
        try:
            if method == "OPTIONS":
                self.send_response(204)
                for k, v in CORS_HEADERS.items():
                    self.send_header(k, v)
                self.end_headers()
                return

            if path == "/api/users" and method == "GET":
                self._handle_list_users()
            elif path == "/api/enroll" and method == "POST":
                self._handle_enroll()
            elif path == "/api/revoke" and method == "POST":
                self._handle_revoke()
            elif path == "/api/toggle-totp" and method == "POST":
                self._handle_toggle_totp()
            elif path in ("/health", "/api/health") and method == "GET":
                self._send_json(200, {"status": "ok"})
            else:
                self._send_json(404, {"error": "Route inconnue."})
        except APIError as exc:
            self._send_json(exc.status, {"error": str(exc)})
        except Exception as exc:  # noqa: BLE001
            self._send_json(500, {"error": f"Erreur interne : {exc}"})

    def do_GET(self):  # noqa: N802
        self._route("GET")

    def do_POST(self):  # noqa: N802
        self._route("POST")

    def do_OPTIONS(self):  # noqa: N802
        self._route("OPTIONS")


    def _handle_list_users(self) -> None:
        """GET /api/users : liste les agents (hors user technique interne)."""
        synapse_users = synapse_list_users()
        kc_users = kc_list_users()
        kc_map = {u["username"]: u for u in kc_users}

        result = []
        for u in synapse_users:
            name = u.get("name", "")
            if not name.startswith("@"):
                continue
            username = name[1:].split(":", 1)[0]
            if username == _TECH_USER or username.startswith("sys_"):
                continue  # masquer les comptes techniques internes
            kc = kc_map.get(username, {})
            req_actions = kc.get("requiredActions") or []
            totp_required = "CONFIGURE_TOTP" in req_actions
            has_totp = False
            if kc.get("id"):
                try:
                    creds = _kc_call(
                        "GET",
                        f"/admin/realms/kibare/users/{quote(kc['id'], safe='')}/credentials",
                    )
                    has_totp = any(c.get("type") == "otp" for c in creds)
                except Exception:
                    pass

            result.append({
                "user_id": name,
                "username": username,
                "displayname": u.get("displayname") or username,
                "admin": u.get("admin", False),
                "deactivated": u.get("deactivated", False),
                "kc_enabled": kc.get("enabled", False),
                "totp_required": totp_required,
                "has_totp": has_totp,
                "last_seen_ts": u.get("last_seen_ts"),
            })
        self._send_json(200, {"users": result})

    def _handle_enroll(self) -> None:
        """POST /api/enroll : crée un compte dans Keycloak et Synapse."""
        data = self._read_json()
        username = (data.get("username") or "").strip().lower()
        display_name = (data.get("display_name") or "").strip()
        password = data.get("password") or ""
        require_totp = bool(data.get("require_totp", False))

        if not username or not USERNAME_RE.fullmatch(username):
            raise APIError(
                "Identifiant invalide : lettres minuscules, chiffres, '.', '_' ou '-', 1 à 64 caractères."
            )
        if not display_name:
            raise APIError("Le nom complet est requis.")
        if len(password) < 14:
            raise APIError("Le mot de passe temporaire doit contenir au moins 14 caractères.")
        if username in ("admin", _TECH_USER):
            raise APIError(f"L'identifiant « {username} » est réservé.")

        existing = kc_find_user(username)
        if existing:
            if existing.get("enabled", True):
                # Compte actif : vrai conflit
                raise APIError(f"L'identifiant « {username} » est déjà actif dans Keycloak.", 409)
            # Compte révoqué : le supprimer pour permettre la réinscription
            kc_delete_user(existing["id"])

        kc_uid = kc_create_user(username, display_name, password, require_totp=require_totp)

        try:
            if synapse_user_exists(username):
                # Réactiver le compte Synapse existant (Synapse ne supprime jamais vraiment les users)
                synapse_create_user(username, display_name)
            else:
                synapse_create_user(username, display_name)
        except APIError as exc:
            # Compensation : supprime le compte Keycloak si Synapse échoue
            try:
                kc_delete_user(kc_uid)
            except APIError:
                pass
            raise APIError(f"Synapse : {exc}. Le compte Keycloak a été supprimé.") from exc

        totp_msg = (
            "Configuration 2FA (TOTP) exigée à la première connexion."
            if require_totp
            else "Configuration 2FA (TOTP) optionnelle."
        )
        self._send_json(201, {
            "ok": True,
            "user_id": f"@{username}:{SERVER_NAME}",
            "message": f"Compte « {username} » créé avec succès. {totp_msg}",
        })

    def _handle_toggle_totp(self) -> None:
        """POST /api/toggle-totp : active ou désactive l'exigence TOTP pour un compte."""
        data = self._read_json()
        username = (data.get("username") or "").strip().lower()
        require_totp = bool(data.get("require_totp", False))
        if not username:
            raise APIError("Le champ « username » est requis.")
        kc_toggle_totp(username, require_totp)
        status_label = "exigée à la connexion" if require_totp else "rendue optionnelle"
        self._send_json(200, {
            "ok": True,
            "username": username,
            "totp_required": require_totp,
            "message": f"Double authentification {status_label} pour « {username} ».",
        })

    def _handle_revoke(self) -> None:
        """POST /api/revoke : désactive un compte dans Synapse et Keycloak."""
        data = self._read_json()
        username = (data.get("username") or "").strip()

        if not username:
            raise APIError("Le champ « username » est requis.")
        if username in ("admin", _TECH_USER):
            raise APIError("Ce compte ne peut pas être révoqué via l'interface web.")

        synapse_deactivate_user(username)
        kc_deactivate_user(username)

        self._send_json(200, {
            "ok": True,
            "message": f"Compte « @{username}:{SERVER_NAME} » désactivé et sessions révoquées.",
        })


# Point d'entrée

if __name__ == "__main__":
    if not REG_SECRET:
        raise SystemExit("[ERREUR] SYNAPSE_REGISTRATION_SHARED_SECRET est absent.")
    if not KC_ADMIN_PASS:
        raise SystemExit("[ERREUR] KEYCLOAK_ADMIN_PASSWORD est absent.")

    print(f"[INFO] Kibare Admin API : démarrage sur 0.0.0.0:{LISTEN_PORT}", flush=True)

    try:
        _get_synapse_admin_token()
        print("[INFO] Token technique Synapse initialisé.", flush=True)
    except APIError as _e:
        print(f"[AVERTISSEMENT] Token Synapse non initialisé au démarrage : {_e}", flush=True)

    server = http.server.ThreadingHTTPServer(("0.0.0.0", LISTEN_PORT), AdminAPIHandler)
    print(f"[INFO] En écoute sur le port {LISTEN_PORT}.", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[INFO] Arrêt.", flush=True)
