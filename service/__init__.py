import logging
from datetime import datetime, timedelta
from enum import StrEnum

import pytz

from database import Database
from service.login import LoginService
from service.notifications import NotificationsService
from service.responses import ErrorCode, ErrorResponse, ServiceResponse, SuccessResponse

logger = logging.getLogger(__name__)


class ProgressResult(StrEnum):
    """Enum for progress result types."""

    KNOW = "know"
    REVISE = "revise"


class Service(LoginService):
    """Service class for handling flashcard operations."""

    def __init__(self, db=None):
        self.db = db or Database()
        self.notifications = NotificationsService()

    @staticmethod
    def error_handler(func):
        """Decorator to handle errors in service methods and return standardized error responses."""

        def wrapper(*args, **kwargs) -> ServiceResponse:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.error(f"An error occurred in {func.__name__}: {e}")
                return ErrorResponse(message=str(e), code=ErrorCode.INTERNAL_ERROR)

        wrapper.__name__ = func.__name__
        return wrapper

    @error_handler
    def get_decks(self) -> ServiceResponse:
        decks = self.db.get_decks()
        data = [{"id": d["id"], "name": d["name"]} for d in decks]
        return SuccessResponse(data)

    @error_handler
    def get_next_card(self, deck_id: int) -> ServiceResponse:
        deck = self.db.get_deck(deck_id)
        if not deck:
            logger.warning(f"Deck with ID {deck_id} not found.")
            return ErrorResponse("Deck not found", ErrorCode.NOT_FOUND)

        deck_data = {"id": deck["id"], "name": deck["name"]}
        card = self.db.get_next_card(deck_id)
        if not card:
            return SuccessResponse({"card": None, "deck": deck_data})

        card_data = {"id": card["id"], "front": card["front"], "back": card["back"]}
        return SuccessResponse({"card": card_data, "deck": deck_data})

    @error_handler
    def update_card_progress(self, card_id: int, result: str) -> ServiceResponse:
        if result not in {ProgressResult.KNOW, ProgressResult.REVISE}:
            logger.warning(f"Invalid result value: {result}")
            return ErrorResponse("Invalid `result` value", ErrorCode.VALIDATION_ERROR)

        card = self.db.get_card(card_id)
        if not card:
            logger.warning(f"Card with ID {card_id} not found.")
            return ErrorResponse("Card not found", ErrorCode.NOT_FOUND)

        self.db.update_card_progress(card_id, result)
        return SuccessResponse()

    @error_handler
    def reset_progress(self, deck_id: int) -> ServiceResponse:
        self.db.reset_deck_progress(deck_id)
        return SuccessResponse()

    @error_handler
    def verify_login_code(self, email: str, code: str) -> ServiceResponse:
        entry = self.db.get_login_code(email)
        if not entry or datetime.fromisoformat(entry["expires_at"]) < datetime.now(pytz.utc):
            return ErrorResponse("Invalid or expired code", ErrorCode.UNAUTHORIZED)
        if entry["attempts"] >= self.MAX_ATTEMPTS:
            return ErrorResponse("Maximum attempts exceeded", ErrorCode.TOO_MANY_REQUESTS)

        self.db.increment_login_code_attempts(entry["id"])

        if entry["code_hash"] != self._hash_code(code, email):
            return ErrorResponse("Invalid code", ErrorCode.UNAUTHORIZED)

        self.db.set_login_code_used(entry["id"])

        user = self.db.get_user_by_email(email)
        if not user:
            logger.warning("User not found. Registration is limited at this moment.")
            return ErrorResponse("User not found", ErrorCode.NOT_FOUND)

        return SuccessResponse({"id": user["id"], "email": user["email"]})

    @error_handler
    def send_login_code(self, email: str) -> ServiceResponse:
        if not self.db.get_user_by_email(email):
            return ErrorResponse("User not found", ErrorCode.NOT_FOUND)

        code = self._generate_code()
        hashed_code = self._hash_code(code, email)
        expires_at = datetime.now(pytz.utc) + timedelta(minutes=self.CODE_TTL_MINUTES)
        self.db.add_login_code(email, hashed_code, expires_at)

        self.notifications.send_verification_code(email, code)

        return SuccessResponse(message="Login code sent successfully")

    def health_check(self) -> ServiceResponse:
        """Check the health of the service."""

        if not self.db.health_check():
            logger.error("Database connection failed.")
            return ErrorResponse("Database connection failed", ErrorCode.INTERNAL_ERROR)
        if not self.notifications.health_check():
            logger.error("Notifications service health check failed.")
            return ErrorResponse("Notifications service health check failed", ErrorCode.INTERNAL_ERROR)
        return SuccessResponse()
