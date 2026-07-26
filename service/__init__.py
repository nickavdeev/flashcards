import logging
from enum import StrEnum

from database import Database
from service.responses import ErrorCode, ErrorResponse, ServiceResponse, SuccessResponse

logger = logging.getLogger(__name__)


class ProgressResult(StrEnum):
    """Enum for progress result types."""

    KNOW = "know"
    REVISE = "revise"


class Service:
    """Service class for handling flashcard operations."""

    def __init__(self, db=None):
        self.db = db or Database()

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

    def health_check(self) -> ServiceResponse:
        """Check the health of the service by verifying the database connection."""

        if not self.db.health_check():
            logger.error("Database connection failed.")
            return ErrorResponse("Database connection failed", ErrorCode.INTERNAL_ERROR)
        return SuccessResponse()
