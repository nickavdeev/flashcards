import unittest
from unittest.mock import MagicMock

from flask_login import FlaskLoginClient

from app import User, create_app


class TestApp(unittest.TestCase):
    def setUp(self):
        service = MagicMock()
        self.app = create_app(service=service)
        self.app.config["TESTING"] = True
        self.app.test_client_class = FlaskLoginClient

        self.email = "test@example.com"
        self.unauthenticated_client = self.app.test_client()
        self.client = self.app.test_client(user=User(1, self.email))


class TestApiRoutes(TestApp):
    def test_get_decks_returns_200(self):
        self.app.service.get_decks.return_value = {
            "ok": True,
            "status_code": 200,
            "data": [{"id": 1, "name": "German"}],
        }

        response = self.client.get("/api/v1/decks")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertEqual(response.get_json()["data"], [{"id": 1, "name": "German"}])

    def test_update_card_progress_passes_result_query_param(self):
        self.app.service.update_card_progress.return_value = {"ok": True, "status_code": 200}

        response = self.client.post("/api/v1/cards/42/review?result=know")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.app.service.update_card_progress.assert_called_once_with(42, "know")

    def test_update_card_progress_missing_result_param(self):
        response = self.client.post("/api/v1/cards/42/review")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["ok"], False)

    def test_get_next_card_returns_200(self):
        self.app.service.get_next_card.return_value = {
            "ok": True,
            "status_code": 200,
            "data": {"card": {"id": 101, "front": "Q1", "back": "A1"}, "deck": {"id": 1, "name": "Deck 1"}},
        }

        response = self.client.get("/api/v1/deck/1/cards/next")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertEqual(response.get_json()["data"]["deck"]["id"], 1)
        self.assertEqual(response.get_json()["data"]["card"]["id"], 101)

    def test_reset_progress_returns_200(self):
        self.app.service.reset_progress.return_value = {"ok": True, "status_code": 200}

        response = self.client.post("/api/v1/deck/1/reset")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.app.service.reset_progress.assert_called_once_with(1)

    def test_request_code_returns_200(self):
        self.app.service.send_login_code.return_value = {
            "ok": True, "data": {"message": "Login code sent successfully"}
        }

        response = self.client.post("/api/v1/request-code", json={"email": self.email})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertEqual(response.get_json()["data"]["message"], "Login code sent successfully")

    def test_request_code_missing_email_param_returns_400(self):
        response = self.client.post("/api/v1/request-code", json={})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["ok"], False)

    def test_login_returns_200_on_successful_login(self):
        self.app.service.verify_login_code.return_value = {
            "ok": True, "data": {"id": 1, "email": self.email},
        }

        response = self.client.post("/api/v1/login", json={"email": self.email, "code": "123456"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertIn("Logged in successfully", response.get_json()["message"])

    def test_login_returns_401_on_invalid_code(self):
        self.app.service.verify_login_code.return_value = {
            "ok": False, "code": "unauthorized", "message": "Invalid code",
        }

        response = self.client.post("/api/v1/login", json={"email": self.email, "code": "000000"})

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.get_json()["ok"], False)
        self.assertIn("Invalid code", response.get_json()["message"])

    def test_login_missing_required_params_returns_400(self):
        for missing_param in ["email", "code"]:
            payload = {"email": self.email, "code": "123456"}
            with self.subTest(param=missing_param):
                payload.pop(missing_param)

                response = self.client.post("/api/v1/login", json=payload)

                self.assertEqual(response.status_code, 400)
                self.assertEqual(response.get_json()["ok"], False)

    def test_logout_returns_200(self):
        response = self.client.post("/api/v1/logout")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get_json()["ok"], True)
        self.assertIn("Logged out successfully", response.get_json()["message"])


class TestHealth(TestApp):
    def test_health_returns_200_when_db_ok(self):
        self.app.service.health_check.return_value = True

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, b"OK")

    def test_health_returns_500_when_service_unavailable(self):
        self.app.service.health_check.return_value = False

        response = self.client.get("/health")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.data, b"Service Unavailable")


class TestPages(TestApp):
    def test_login_page_renders(self):
        response = self.unauthenticated_client.get("/login")
        self.assertEqual(response.status_code, 200)

    def test_login_page_redirects_when_authenticated(self):
        response = self.client.get("/login")
        self.assertEqual(response.status_code, 302)
        self.assertIn("/", response.headers["Location"])

    def test_main_page_renders_for_all_users(self):
        response = self.unauthenticated_client.get("/")
        self.assertEqual(response.status_code, 200)

        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_deck_page_requires_login(self):
        response = self.unauthenticated_client.get("/deck/1")
        self.assertEqual(response.status_code, 401)

    def test_deck_page_renders_with_valid_id(self):
        response = self.client.get("/deck/5")
        self.assertEqual(response.status_code, 200)

    def test_deck_page_rejects_non_integer_id(self):
        response = self.client.get("/deck/not-an-integer")
        self.assertEqual(response.status_code, 404)
