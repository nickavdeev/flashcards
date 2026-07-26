import unittest
from unittest.mock import MagicMock

from app import create_app


class TestApp(unittest.TestCase):
    def setUp(self):
        service = MagicMock()
        self.app = create_app(service=service)
        self.app.config["TESTING"] = True
        self.client = self.app.test_client()


class TestApiRoutes(TestApp):
    def test_get_decks_returns_200(self):
        self.app.service.get_decks.return_value = {
            "ok": True,
            "status_code": 200,
            "data": [{"id": 1, "name": "German"}],
        }

        response = self.client.get("/api/v1/decks")

        print(response.get_json())

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
        self.app.service.update_card_progress.return_value = {
            "ok": False,
            "code": "validation_error",
            "message": "Invalid `result` value",
        }

        response = self.client.post("/api/v1/cards/42/review")

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.get_json()["ok"], False)
        self.assertIn("Invalid `result` value", response.get_json()["message"])
        self.app.service.update_card_progress.assert_called_once_with(42, None)

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
    def test_main_page_renders(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)

    def test_deck_page_renders_with_valid_id(self):
        response = self.client.get("/deck/5")
        self.assertEqual(response.status_code, 200)

    def test_deck_page_rejects_non_integer_id(self):
        response = self.client.get("/deck/not-an-integer")
        self.assertEqual(response.status_code, 404)
