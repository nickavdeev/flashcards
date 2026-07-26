import logging
import os
import sqlite3
import threading
from datetime import datetime

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class Database:
    """Class to handle database operations for flashcards."""

    def __init__(self, conn: sqlite3.Connection = None):
        self.conn = conn or self._create_connection()
        self._lock = threading.Lock()

    @staticmethod
    def _create_connection():
        conn = sqlite3.connect(
            os.getenv("DATABASE_NAME", "flashcards.db"),
            check_same_thread=False,
        )
        conn.row_factory = sqlite3.Row
        return conn

    def _fetch_data(self, query, params=None, fetch_one=False):
        with self._lock:
            cursor = self.conn.cursor()
            cursor.execute(query, params or ())
            return cursor.fetchone() if fetch_one else cursor.fetchall()

    def _execute_query(self, query, params=None):
        with self._lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute(query, params or ())
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise

    def health_check(self):
        with self._lock:
            cursor = self.conn.cursor()
            try:
                cursor.execute("SELECT 1")
                return True
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                return False

    def get_decks(self):
        query = "SELECT id, name FROM decks"
        return self._fetch_data(query)

    def update_card_progress(self, card_id, result):
        query, params = "SELECT card_id FROM card_progress WHERE card_id = ?", (card_id,)
        existing = self._fetch_data(query, params, fetch_one=True)

        now = datetime.now().isoformat() + "Z"
        params = (result, now, card_id)
        if existing:
            query = "UPDATE card_progress SET last_result = ?, last_reviewed_at = ? WHERE card_id = ?"
            self._execute_query(query, params)
        else:
            query = "INSERT INTO card_progress (last_result, last_reviewed_at, card_id) VALUES (?, ?, ?)"
            self._execute_query(query, params)

    def get_deck(self, deck_id):
        query, params = "SELECT id, name FROM decks WHERE id = ?", (deck_id,)
        return self._fetch_data(query, params, fetch_one=True)

    def get_next_card(self, deck_id):
        query, params = (
            """
            SELECT c.id, c.front, c.back
            FROM cards c
            LEFT JOIN card_progress p ON p.card_id = c.id
            WHERE c.deck_id = ? AND (p.card_id IS NULL OR p.last_result = 'revise')
            ORDER BY p.last_reviewed_at
            LIMIT 1
            """,
            (deck_id,),
        )
        return self._fetch_data(query, params, fetch_one=True)

    def get_card(self, card_id):
        query, params = "SELECT id FROM cards WHERE id = ?", (card_id,)
        return self._fetch_data(query, params, fetch_one=True)

    def reset_deck_progress(self, deck_id):
        query, params = (
            "DELETE FROM card_progress WHERE card_id IN (SELECT id FROM cards WHERE deck_id = ?)",
            (deck_id,),
        )
        self._execute_query(query, params)
