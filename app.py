import os

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request

from service import Service
from service.responses import ErrorCode
from settings import setup_logging

load_dotenv()

setup_logging()


ERROR_CODE_TO_HTTP = {
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.INTERNAL_ERROR: 500,
}


class FlashcardsApp(Flask):
    """Flask application for the flashcards app."""

    def __init__(self, service=None):
        super().__init__(__name__)

        self.config["ENV"] = os.getenv("ENVIRONMENT")
        self.config["DEBUG"] = self.config["ENV"] == "development"
        self.config["DATABASE_NAME"] = os.getenv("DATABASE_NAME")

        self.service = service or Service()

    def register_routes(self):
        page_routes = [
            ("/", "main_page", self.main_page),
            ("/deck/<int:deck_id>", "deck_page", self.deck_page),
        ]
        api_v1_routes = [
            ("cards/<int:card_id>/review", self.update_card_progress, ["POST"]),
            ("decks", self.get_decks, ["GET"]),
            ("deck/<int:deck_id>/cards/next", self.get_next_card, ["GET"]),
            ("deck/<int:deck_id>/reset", self.reset_progress, ["POST"]),
        ]
        monitoring_routes = [
            ("/health", "health", self.health),
        ]

        for route in page_routes:
            self.add_url_rule(*route)
        for route, func, methods in api_v1_routes:
            self.add_url_rule(f"/api/v1/{route}", view_func=func, methods=methods)
        for route in monitoring_routes:
            self.add_url_rule(*route)

    @staticmethod
    def api_response(response):
        """Helper method to format API responses."""
        status = 200 if response["ok"] else ERROR_CODE_TO_HTTP[response["code"]]
        return jsonify(response), status

    def get_decks(self):
        data = self.service.get_decks()
        return self.api_response(data)

    def update_card_progress(self, card_id):
        result = request.args.get("result")
        data = self.service.update_card_progress(card_id, result)
        return self.api_response(data)

    def get_next_card(self, deck_id):
        data = self.service.get_next_card(deck_id)
        return self.api_response(data)

    def reset_progress(self, deck_id):
        data = self.service.reset_progress(deck_id)
        return self.api_response(data)

    @staticmethod
    def deck_page(*args, **kwargs):
        return render_template("deck.html")

    @staticmethod
    def main_page():
        return render_template("index.html")

    def health(self):
        if not self.service.health_check():
            return "Service Unavailable", 500
        return "OK", 200


def create_app(service=None):
    """Entry point for creating the Flask application."""

    flashcards_app = FlashcardsApp(service=service)
    flashcards_app.register_routes()

    return flashcards_app


if __name__ == "__main__":
    app = create_app(service=Service())
    app.run()
