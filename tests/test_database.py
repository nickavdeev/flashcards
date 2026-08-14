import sqlite3
import unittest

from database import Database

SCHEMA = """
PRAGMA foreign_keys = ON;

CREATE TABLE users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE login_codes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT NOT NULL,
    code_hash TEXT NOT NULL,
    expires_at DATETIME NOT NULL,
    attempts INTEGER DEFAULT 0,
    used BOOLEAN DEFAULT 0,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE decks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE cards (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    deck_id INTEGER REFERENCES decks(id),
    front TEXT NOT NULL,
    back TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE card_progress (
    card_id INTEGER PRIMARY KEY REFERENCES cards(id),
    last_result TEXT NOT NULL,
    last_reviewed_at TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""


class TestDatabase(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.conn.row_factory = sqlite3.Row
        self.conn.executescript(SCHEMA)
        self.db = Database(conn=self.conn)

        self.email = "test@example.com"

    def tearDown(self):
        self.conn.close()


class TestGetDecks(TestDatabase):
    def test_returns_all_decks(self):
        self.conn.execute("INSERT INTO decks (name) VALUES ('English')")
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.commit()

        decks = self.db.get_decks()

        self.assertEqual(len(decks), 2)
        self.assertEqual(decks[0]["name"], "English")
        self.assertEqual(decks[1]["name"], "German")

    def test_returns_empty_when_no_decks(self):
        decks = self.db.get_decks()

        self.assertEqual(decks, [])

    def test_returns_decks_with_correct_columns(self):
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.commit()

        decks = self.db.get_decks()

        self.assertEqual(set(decks[0].keys()), {"id", "name"})


class TestGetDeck(TestDatabase):
    def test_returns_deck_by_id(self):
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.commit()

        deck = self.db.get_deck(1)

        self.assertIsNotNone(deck)
        self.assertEqual(deck["name"], "German")
        self.assertEqual(set(deck.keys()), {"id", "name"})

    def test_returns_none_for_nonexistent_deck(self):
        deck = self.db.get_deck(999)

        self.assertIsNone(deck)


class TestGetNextCard(TestDatabase):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")

    def test_returns_next_card_in_deck(self):
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q2', 'A2')")
        self.conn.commit()

        card = self.db.get_next_card(1)

        self.assertIsNotNone(card)
        self.assertEqual(card["front"], "Q1")

    def test_returns_none_when_no_cards_in_deck(self):
        card = self.db.get_next_card(1)

        self.assertIsNone(card)

    def test_returns_none_when_all_cards_reviewed(self):
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (1, 'know', '2026-01-01T00:00:00Z')"
        )
        self.conn.commit()

        card = self.db.get_next_card(1)

        self.assertIsNone(card)

    def test_returns_card_with_revise_result(self):
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (1, 'revise', '2026-01-01T00:00:00Z')"
        )
        self.conn.commit()

        card = self.db.get_next_card(1)

        self.assertIsNotNone(card)
        self.assertEqual(card["front"], "Q1")

    def test_returns_next_card_ordered_by_last_reviewed_at(self):
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q2', 'A2')")
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (1, 'revise', '2026-01-02T00:00:00Z')"
        )
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (2, 'revise', '2026-01-01T00:00:00Z')"
        )
        self.conn.commit()

        card = self.db.get_next_card(1)

        self.assertIsNotNone(card)
        self.assertEqual(card["front"], "Q2")  # Q2 was reviewed earlier than Q1

    def test_returns_card_with_no_progress_first(self):
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q2', 'A2')")
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (1, 'know', '2026-01-01T00:00:00Z')"
        )
        self.conn.commit()

        card = self.db.get_next_card(1)

        self.assertIsNotNone(card)
        self.assertEqual(card["front"], "Q2")  # Q2 has no progress and should be returned


class TestGetCard(TestDatabase):
    def test_returns_card_by_id(self):
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.commit()

        card = self.db.get_card(1)

        self.assertIsNotNone(card)
        self.assertEqual(card["id"], 1)

    def test_returns_none_for_nonexistent_card(self):
        card = self.db.get_card(999)

        self.assertIsNone(card)


class TestUpdateCardProgress(TestDatabase):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.commit()

    def test_inserts_new_progress_record(self):
        self.conn.commit()

        self.db.update_card_progress(card_id=1, result="know")
        progress = self.conn.execute("SELECT * FROM card_progress WHERE card_id = 1").fetchone()

        self.assertIsNotNone(progress)
        self.assertEqual(progress["last_result"], "know")

    def test_updates_existing_progress_record(self):
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (1, 'revise', '2026-01-01T00:00:00Z')"
        )
        self.conn.commit()

        self.db.update_card_progress(card_id=1, result="know")
        progress = self.conn.execute("SELECT * FROM card_progress WHERE card_id = 1").fetchone()

        self.assertIsNotNone(progress)
        self.assertEqual(progress["last_result"], "know")


class TestResetDeckProgress(TestDatabase):
    def setUp(self):
        super().setUp()
        self.conn.execute("INSERT INTO decks (name) VALUES ('German')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (1, 'Q1', 'A1')")
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (1, 'know', '2026-01-01T00:00:00Z')"
        )
        self.conn.commit()

    def test_resets_progress_for_deck(self):
        self.db.reset_deck_progress(deck_id=1)
        progress = self.conn.execute("SELECT * FROM card_progress WHERE card_id = 1").fetchone()

        self.assertIsNone(progress)

    def test_reset_progress_for_nonexistent_deck(self):
        self.db.reset_deck_progress(deck_id=999)
        progress = self.conn.execute("SELECT * FROM card_progress WHERE card_id = 1").fetchone()

        self.assertIsNotNone(progress)
        self.assertEqual(progress["last_result"], "know")

    def test_not_affect_progress_of_other_decks(self):
        self.conn.execute("INSERT INTO decks (name) VALUES ('English')")
        self.conn.execute("INSERT INTO cards (deck_id, front, back) VALUES (2, 'Q2', 'A2')")
        self.conn.execute(
            "INSERT INTO card_progress (card_id, last_result, last_reviewed_at)"
            "VALUES (2, 'revise', '2026-01-02T00:00:00Z')"
        )
        self.conn.commit()

        self.db.reset_deck_progress(deck_id=1)

        progress = self.conn.execute("SELECT * FROM card_progress WHERE card_id = 2").fetchone()

        self.assertIsNotNone(progress)
        self.assertEqual(progress["last_result"], "revise")


class TestUserLogin(TestDatabase):
    def test_get_user_by_email(self):
        self.conn.execute("INSERT INTO users (email) VALUES (?)", (self.email,))
        self.conn.commit()

        user = self.db.get_user_by_email(self.email)

        self.assertIsNotNone(user)
        self.assertEqual(user["email"], self.email)

    def test_add_login_code(self):
        code = "hashed_code"
        expires_at = "2026-01-01T00:00:00Z"
        self.db.add_login_code(self.email, code, expires_at)

        login_code = self.conn.execute(
            "SELECT * FROM login_codes WHERE email = ?", (self.email,)
        ).fetchone()

        self.assertIsNotNone(login_code)
        self.assertEqual(login_code["code_hash"], code)
        self.assertEqual(login_code["expires_at"], expires_at)

    def test_get_login_code(self):
        code = "hashed_code"
        expires_at = "2026-01-01T00:00:00Z"
        self.conn.execute(
            "INSERT INTO login_codes (email, code_hash, expires_at) VALUES (?, ?, ?)",
            (self.email, code, expires_at),
        )
        self.conn.commit()

        login_code = self.db.get_login_code(self.email)

        self.assertIsNotNone(login_code)
        self.assertEqual(login_code["code_hash"], code)
        self.assertEqual(login_code["expires_at"], expires_at)

    def test_increment_login_code_attempts(self):
        code = "hashed_code"
        expires_at = "2026-01-01T00:00:00Z"
        self.conn.execute(
            "INSERT INTO login_codes (email, code_hash, expires_at, attempts) VALUES (?, ?, ?, ?)",
            (self.email, code, expires_at, 0),
        )
        self.conn.commit()

        self.db.increment_login_code_attempts(code_id=1)

        login_code = self.conn.execute(
            "SELECT * FROM login_codes WHERE email = ?", (self.email,)
        ).fetchone()

        self.assertIsNotNone(login_code)
        self.assertEqual(login_code["attempts"], 1)

    def test_set_login_code_used(self):
        code = "hashed_code"
        expires_at = "2026-01-01T00:00:00Z"
        self.conn.execute(
            "INSERT INTO login_codes (email, code_hash, expires_at, used) VALUES (?, ?, ?, ?)",
            (self.email, code, expires_at, 0),
        )
        self.conn.commit()

        self.db.set_login_code_used(code_id=1)

        login_code = self.conn.execute(
            "SELECT * FROM login_codes WHERE email = ?", (self.email,)
        ).fetchone()

        self.assertIsNotNone(login_code)
        self.assertEqual(login_code["used"], 1)

