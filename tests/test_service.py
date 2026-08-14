import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock

import pytz

from service import Service


class TestService(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.service = Service(db=self.mock_db)

        self.mock_db.get_decks.return_value = [{"id": 1, "name": "Deck 1"}, {"id": 2, "name": "Deck 2"}]
        self.mock_db.get_deck.return_value = {"id": 1, "name": "Deck 1"}
        self.mock_db.get_next_card.return_value = {"id": 101, "front": "Q1", "back": "A1"}
        self.mock_db.get_card.return_value = {"id": 101, "front": "Q1", "back": "A1"}

        self.email = "test@example.com"


class TestDecks(TestService):
    def test_returns_all_decks(self):
        response = self.service.get_decks()

        self.assertEqual(response["ok"], True)
        self.assertEqual(len(response["data"]), 2)
        self.assertEqual(response["data"][0]["id"], 1)
        self.assertEqual(response["data"][0]["name"], "Deck 1")

    def test_db_error_handling(self):
        self.mock_db.get_decks.side_effect = Exception("Database error")

        response = self.service.get_decks()

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Database error", response["message"])


class TestGetNextCard(TestService):
    def test_returns_next_card(self):
        response = self.service.get_next_card(deck_id=1)

        self.assertEqual(response["ok"], True)
        self.assertEqual(response["data"]["deck"], {"id": 1, "name": "Deck 1"})
        self.assertEqual(response["data"]["card"], {"id": 101, "front": "Q1", "back": "A1"})

    def test_returns_none_when_no_next_card(self):
        self.mock_db.get_next_card.return_value = None

        response = self.service.get_next_card(deck_id=1)

        self.assertEqual(response["ok"], True)
        self.assertEqual(response["data"]["deck"], {"id": 1, "name": "Deck 1"})
        self.assertEqual(response["data"]["card"], None)

    def test_deck_not_found(self):
        self.mock_db.get_deck.return_value = None

        response = self.service.get_next_card(deck_id=1)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "not_found")
        self.assertEqual("Deck not found", response["message"])


class TestUpdateCardProgress(TestService):
    def test_returns_success_for_valid_results(self):
        for result in ["know", "revise"]:
            response = self.service.update_card_progress(card_id=101, result=result)

            self.assertEqual(response["ok"], True)

    def test_returns_error_for_invalid_result(self):
        response = self.service.update_card_progress(card_id=101, result="incorrect")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "validation_error")
        self.assertEqual("Invalid `result` value", response["message"])

    def test_returns_error_when_card_not_found(self):
        self.mock_db.get_card.return_value = None

        response = self.service.update_card_progress(card_id=101, result="know")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "not_found")
        self.assertEqual("Card not found", response["message"])

    def test_db_error_handling(self):
        self.mock_db.get_card.side_effect = Exception("Database error")

        response = self.service.update_card_progress(card_id=101, result="know")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Database error", response["message"])


class TestResetProgress(TestService):
    def test_returns_success(self):
        response = self.service.reset_progress(deck_id=1)

        self.assertEqual(response["ok"], True)

    def test_db_error_handling(self):
        self.mock_db.reset_deck_progress.side_effect = Exception("Database error")

        response = self.service.reset_progress(deck_id=1)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Database error", response["message"])


class TestUserLogin(TestService):
    def test_send_login_code_success(self):
        self.service.notifications._send_email = MagicMock()

        response = self.service.send_login_code(email=self.email)

        self.assertEqual(response["ok"], True)
        self.assertEqual("Login code sent successfully", response["message"])

    def test_send_login_code_db_error(self):
        self.mock_db.add_login_code.side_effect = Exception("Database error")

        response = self.service.send_login_code(email=self.email)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Database error", response["message"])

    def test_send_login_code_email_error(self):
        self.service.notifications.send_verification_code = MagicMock(
            side_effect=Exception("Failed to send login code")
        )

        response = self.service.send_login_code(email=self.email)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Failed to send login code", response["message"])

    def test_verify_login_code_success(self):
        self.mock_db.get_login_code.return_value = {
            "id": 1,
            "code_hash": self.service._hash_code("123456", self.email),
            "expires_at": (datetime.now(pytz.utc) + timedelta(minutes=5)).isoformat(),
            "attempts": 0
        }
        self.mock_db.get_user_by_email.return_value = {"id": 1, "email": self.email}

        response = self.service.verify_login_code(email=self.email, code="123456")

        self.assertEqual(response["ok"], True)
        self.assertEqual(response["data"]["id"], 1)

    def test_verify_login_code_invalid_or_expired(self):
        self.mock_db.get_login_code.return_value = None

        response = self.service.verify_login_code(email=self.email, code="123456")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "unauthorized")
        self.assertEqual("Invalid or expired code", response["message"])

        self.mock_db.get_login_code.return_value = {
            "id": 1,
            "code_hash": self.service._hash_code("123456", self.email),
            "expires_at": (datetime.now(pytz.utc) - timedelta(minutes=5)).isoformat(),
            "attempts": 0
        }

        response = self.service.verify_login_code(email=self.email, code="123456")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "unauthorized")
        self.assertEqual("Invalid or expired code", response["message"])

    def test_verify_login_code_max_attempts_exceeded(self):
        self.mock_db.get_login_code.return_value = {
            "id": 1,
            "code_hash": self.service._hash_code("123456", self.email),
            "expires_at": (datetime.now(pytz.utc) + timedelta(minutes=5)).isoformat(),
            "attempts": self.service.MAX_ATTEMPTS
        }

        response = self.service.verify_login_code(email=self.email, code="123456")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "too_many_requests")
        self.assertEqual("Maximum attempts exceeded", response["message"])

    def test_verify_login_code_invalid_code(self):
        self.mock_db.get_login_code.return_value = {
            "id": 1,
            "code_hash": self.service._hash_code("123456", self.email),
            "expires_at": (datetime.now(pytz.utc) + timedelta(minutes=5)).isoformat(),
            "attempts": 0
        }

        response = self.service.verify_login_code(email=self.email, code="wrong_code")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "unauthorized")
        self.assertEqual("Invalid code", response["message"])

    def test_verify_login_code_user_not_found(self):
        self.mock_db.get_login_code.return_value = {
            "id": 1,
            "code_hash": self.service._hash_code("123456", self.email),
            "expires_at": (datetime.now(pytz.utc) + timedelta(minutes=5)).isoformat(),
            "attempts": 0
        }
        self.mock_db.get_user_by_email.return_value = None

        response = self.service.verify_login_code(email=self.email, code="123456")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "not_found")
        self.assertEqual("User not found", response["message"])

    def test_verify_login_code_db_error(self):
        self.mock_db.get_login_code.side_effect = Exception("Database error")

        response = self.service.verify_login_code(email=self.email, code="123456")

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Database error", response["message"])


class TestNotifications(TestService):
    def test_send_verification_code_success(self):
        self.service.notifications._send_email = MagicMock()

        self.service.send_login_code(email=self.email)

        self.service.notifications._send_email.assert_called_once()

    def test_send_verification_code_failure(self):
        self.service.notifications._send_email = MagicMock(side_effect=Exception("Failed to send email"))

        response = self.service.send_login_code(email=self.email)

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Failed to send email", response["message"])


class TestHealthCheck(TestService):
    def test_health_check_success(self):
        self.mock_db.health_check.return_value = True
        self.service.notifications.health_check = MagicMock(return_value=True)

        response = self.service.health_check()

        self.assertEqual(response["ok"], True)

    def test_health_check_db_failure(self):
        self.mock_db.health_check.return_value = False

        response = self.service.health_check()

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Database connection failed", response["message"])

    def test_health_check_notifications_failure(self):
        self.mock_db.health_check.return_value = True
        self.service.notifications.health_check = MagicMock(return_value=False)

        response = self.service.health_check()

        self.assertEqual(response["ok"], False)
        self.assertEqual(response["code"], "internal_error")
        self.assertEqual("Notifications service health check failed", response["message"])
