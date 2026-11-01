import json
import subprocess
import sys
import unittest
from argparse import Namespace
from unittest.mock import Mock, patch

from scripts.kibare_admin import (
    AdminError,
    KeycloakClient,
    SynapseClient,
    enroll,
    matrix_user_id,
    room_payload,
    room_role_payload,
    validate_existing_user_id,
    validate_room_id,
)


class FakeResponse:
    def __init__(self, body):
        self.body = body
        self.headers = {}

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        return False

    def read(self):
        return self.body


class IdentityTests(unittest.TestCase):
    def test_builds_local_matrix_user_id(self):
        self.assertEqual(
            matrix_user_id("amina.traore", "kibare.test"),
            "@amina.traore:kibare.test",
        )

    def test_accepts_fully_qualified_local_user_id(self):
        self.assertEqual(
            matrix_user_id("@amina_traore:kibare.test", "kibare.test"),
            "@amina_traore:kibare.test",
        )

    def test_rejects_invalid_username(self):
        with self.assertRaises(AdminError):
            matrix_user_id("Amina Traoré", "kibare.test")

    def test_rejects_foreign_server_when_creating_user(self):
        with self.assertRaises(AdminError):
            matrix_user_id("@agent:external.example", "kibare.test")

    def test_rejects_user_on_another_homeserver(self):
        with self.assertRaises(AdminError):
            validate_existing_user_id("@agent:external.example", "kibare.test")

    def test_rejects_partial_user_id_for_revocation(self):
        with self.assertRaises(AdminError):
            validate_existing_user_id("agent", "kibare.test")

    def test_api_requests_use_the_admin_bearer_token(self):
        with patch(
            "scripts.kibare_admin.urlopen",
            return_value=FakeResponse(b'{"ok": true}'),
        ) as open_url:
            result = SynapseClient(
                "http://127.0.0.1:8008",
                "fictional-admin-token",
            ).request("POST", "/test", {"example": "value"})

        request = open_url.call_args.args[0]
        self.assertEqual(request.get_header("Authorization"), "Bearer fictional-admin-token")
        self.assertEqual(json.loads(request.data), {"example": "value"})
        self.assertEqual(result, {"ok": True})

    def test_rejects_multiline_access_token_without_exposing_it(self):
        leaked_token = "browser message\nsyt_fictional_sensitive_token"

        with self.assertRaisesRegex(AdminError, "contient plusieurs lignes") as error:
            SynapseClient("http://127.0.0.1:8008", leaked_token)

        self.assertNotIn("syt_fictional_sensitive_token", str(error.exception))

    def test_browser_output_does_not_contaminate_login_token_stdout(self):
        script = """
import os
import webbrowser
from scripts.kibare_admin import open_browser_without_stdout
webbrowser.open = lambda _url: os.write(1, b'Browser chatter\\n')
open_browser_without_stdout('http://127.0.0.1/')
print('MATRIX_ACCESS_TOKEN')
"""
        result = subprocess.run(
            [sys.executable, "-c", script],
            capture_output=True,
            check=True,
        )

        self.assertEqual(result.stdout, b"MATRIX_ACCESS_TOKEN\n")
        self.assertEqual(result.stderr, b"Browser chatter\n")

    def test_enrollment_migrates_existing_matrix_user_without_resetting_password(self):
        client = Mock()
        client.request.return_value = {"name": "@agent:kibare.test"}
        idp = Mock()
        idp.create_user.return_value = "keycloak-user-id"
        args = Namespace(
            username="agent",
            server_name="kibare.test",
            display_name="Agent",
            identity_url="http://127.0.0.1:8082",
        )

        with patch("scripts.kibare_admin.admin_client", return_value=client), patch(
            "scripts.kibare_admin.KeycloakClient", return_value=idp
        ), patch("scripts.kibare_admin.local_env_value", return_value="secret"), patch(
            "scripts.kibare_admin.getpass.getpass",
            side_effect=["fictional-password-123", "fictional-password-123"],
        ):
            enroll(args)

        self.assertEqual(client.request.call_count, 1)
        self.assertEqual(client.request.call_args.args[0], "GET")
        idp.create_user.assert_called_once_with(
            "agent",
            "Agent",
            "fictional-password-123",
        )

    def test_enrollment_rejects_invalid_admin_token_before_prompting_password(self):
        client = Mock()
        client.request.side_effect = AdminError(
            "Invalid access token passed.",
            status_code=401,
        )
        args = Namespace(
            username="agent",
            server_name="kibare.test",
            display_name="Agent",
            identity_url="http://127.0.0.1:8082",
        )

        with patch("scripts.kibare_admin.admin_client", return_value=client), patch(
            "scripts.kibare_admin.getpass.getpass"
        ) as getpass, self.assertRaisesRegex(AdminError, "Invalid access token"):
            enroll(args)

        getpass.assert_not_called()

    def test_enrollment_does_not_silently_reactivate_deactivated_matrix_user(self):
        client = Mock()
        client.request.return_value = {
            "name": "@agent:kibare.test",
            "deactivated": True,
        }
        args = Namespace(
            username="agent",
            server_name="kibare.test",
            display_name="Agent",
            identity_url="http://127.0.0.1:8082",
        )

        with patch("scripts.kibare_admin.admin_client", return_value=client), patch(
            "scripts.kibare_admin.getpass.getpass"
        ) as getpass, self.assertRaisesRegex(AdminError, "est désactivé"):
            enroll(args)

        getpass.assert_not_called()
        client.request.assert_called_once()


class RoomPolicyTests(unittest.TestCase):
    def test_room_is_private_encrypted_non_federated_and_invite_only(self):
        payload = room_payload("Direction générale", ["@amina:kibare.test"])

        self.assertEqual(payload["preset"], "private_chat")
        self.assertEqual(payload["visibility"], "private")
        self.assertEqual(payload["creation_content"], {"m.federate": False})
        self.assertEqual(payload["invite"], ["@amina:kibare.test"])
        encryption = next(
            state for state in payload["initial_state"]
            if state["type"] == "m.room.encryption"
        )
        self.assertEqual(
            encryption["content"]["algorithm"],
            "m.megolm.v1.aes-sha2",
        )
        history = next(
            state for state in payload["initial_state"]
            if state["type"] == "m.room.history_visibility"
        )
        self.assertEqual(history["content"]["history_visibility"], "joined")

    def test_scoped_role_preserves_existing_power_levels(self):
        original = {
            "users_default": 0,
            "events_default": 0,
            "users": {"@admin:kibare.test": 100},
        }

        updated = room_role_payload(
            original,
            "@amina:kibare.test",
            "moderator",
        )

        self.assertEqual(updated["users"]["@amina:kibare.test"], 50)
        self.assertEqual(updated["users"]["@admin:kibare.test"], 100)
        self.assertEqual(original["users"], {"@admin:kibare.test": 100})

    def test_rejects_unknown_role(self):
        with self.assertRaises(AdminError):
            room_role_payload({}, "@amina:kibare.test", "administrator")

    def test_rejects_room_from_another_server(self):
        with self.assertRaises(AdminError):
            validate_room_id("!room:external.example", "kibare.test")


class IdentityProviderTests(unittest.TestCase):
    def test_keycloak_api_requests_use_admin_bearer_token(self):
        client = KeycloakClient(
            "http://127.0.0.1:8082",
            "kcadmin",
            "fictional-admin-password",
        )
        client.access_token = "fictional-keycloak-token"
        with patch(
            "scripts.kibare_admin.urlopen",
            return_value=FakeResponse(b'{"ok": true}'),
        ) as open_url:
            result, _ = client._request("GET", "/admin/realms/kibare/users")

        request = open_url.call_args.args[0]
        self.assertEqual(
            request.get_header("Authorization"),
            "Bearer fictional-keycloak-token",
        )
        self.assertEqual(result, {"ok": True})

    def test_enrollment_sets_temporary_password_and_totp_requirement(self):
        client = KeycloakClient(
            "http://127.0.0.1:8082",
            "kcadmin",
            "fictional-admin-password",
        )
        client.access_token = "fictional-admin-token"
        client.authenticate_admin = Mock()
        client._request = Mock(
            side_effect=[
                ([], None),
                (None, None),
                ([{"id": "idp-user-id", "username": "agent"}], None),
            ]
        )

        user_id = client.create_user("agent", "Test Agent", "temporary-secret")

        self.assertEqual(user_id, "idp-user-id")
        create_payload = client._request.call_args_list[1].args[2]
        self.assertEqual(create_payload["requiredActions"], ["CONFIGURE_TOTP"])
        self.assertTrue(create_payload["credentials"][0]["temporary"])

    def test_realm_template_requires_totp_and_disables_direct_password_grant(self):
        import json
        from pathlib import Path

        template = json.loads(
            Path("keycloak/kibare-realm.json.template").read_text()
        )
        configure_totp = next(
            action
            for action in template["requiredActions"]
            if action["alias"] == "CONFIGURE_TOTP"
        )
        self.assertTrue(configure_totp["enabled"])
        self.assertTrue(configure_totp["defaultAction"])
        client = next(
            app for app in template["clients"]
            if app["clientId"] == "kibare-synapse"
        )
        self.assertFalse(client["directAccessGrantsEnabled"])


if __name__ == "__main__":
    unittest.main()
