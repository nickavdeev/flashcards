import unittest
from unittest.mock import MagicMock

from service import Service


class TestService(unittest.TestCase):
    def setUp(self):
        self.mock_db = MagicMock()
        self.service = Service(db=self.mock_db)

        self.mock_db.get_decks.return_value = [{"id": 1, "name": "Deck 1"}, {"id": 2, "name": "Deck 2"}]
        self.mock_db.get_deck.return_value = {"id": 1, "name": "Deck 1"}
        self.mock_db.get_next_card.return_value = {"id": 101, "front": "Q1", "back": "A1"}
        self.mock_db.get_card.return_value = {"id": 101, "front": "Q1", "back": "A1"}


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
