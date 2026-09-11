import os

from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, request, url_for
from flask_limiter import Limiter, RateLimitExceeded
from flask_limiter.util import get_remote_address
from flask_login import LoginManager, UserMixin, current_user, login_required, login_user, logout_user

from service import Service
from service.responses import ErrorCode, ErrorResponse, ServiceResponse, SuccessResponse
from settings import DEFAULT_RATE_LIMIT, setup_logging

load_dotenv()

setup_logging()


ERROR_CODE_TO_HTTP = {
    ErrorCode.VALIDATION_ERROR: 400,
    ErrorCode.UNAUTHORIZED: 401,
    ErrorCode.NOT_FOUND: 404,
    ErrorCode.TOO_MANY_REQUESTS: 429,
    ErrorCode.INTERNAL_ERROR: 500,
}

limiter = Limiter(key_func=get_remote_address, default_limits=[DEFAULT_RATE_LIMIT])


class User(UserMixin):
    def __init__(self, user_id, email):
        self.id = user_id
        self.email = email


class FlashcardsApp(Flask):
    """Flask application for the flashcards app."""

    def __init__(self, service=None):
        super().__init__(__name__)

        self.config["ENV"] = os.getenv("ENVIRONMENT")
        self.config["DEBUG"] = self.config["ENV"] == "development"
        self.config["DATABASE_NAME"] = os.getenv("DATABASE_NAME")
        self.config["SECRET_KEY"] = os.getenv("SECRET_KEY")

        self.service = service or Service()

        self.register_error_handlers()

    def register_error_handlers(self):
        """Register error handlers for the application."""

        @self.errorhandler(404)
        def not_found_handler(e):  # noqa
            return render_template("errors/404.html"), 404

        @self.errorhandler(RateLimitExceeded)
        def ratelimit_handler(e):  # noqa
            return render_template("errors/429.html"), 429

        @self.errorhandler(500)
        def internal_error_handler(e):  # noqa
            return render_template("errors/500.html"), 500

    @staticmethod
    def _email_or_ip_key():
        """Limiter key function that uses the user's email if available, otherwise falls back to IP address."""
        data = request.get_json(silent=True) or {}
        email = (data.get("email") or "").strip().lower()
        return email or get_remote_address()

    def register_routes(self):
        page_routes = [
            ("/", "main_page", self.main_page),
            ("/deck/<int:deck_id>", "deck_page", self.deck_page),
            ("/login", "login_page", self.login_page),
            ("/api/docs", "api_docs", self.api_docs),
        ]
        api_v1_routes = [
            ("cards/<int:card_id>/review", self.update_card_progress, ["POST"]),
            ("decks", self.get_decks, ["GET"]),
            ("deck/<int:deck_id>/cards/next", self.get_next_card, ["GET"]),
            ("deck/<int:deck_id>/reset", self.reset_progress, ["POST"]),
            ("logout", self.logout, ["POST"])
        ]
        rate_limited_api_v1_routes = [
            ("request-code", self.request_code, ["POST"], "5 per hour", self._email_or_ip_key),
            ("login", self.login, ["POST"], "10 per 15 minutes", self._email_or_ip_key),
        ]
        monitoring_routes = [
            ("/health", "health", self.health),
        ]

        for route in page_routes:
            self.add_url_rule(*route)
        for route, func, methods in api_v1_routes:
            self.add_url_rule(f"/api/v1/{route}", view_func=func, methods=methods)
        for route, func, methods, limit_str, key_func in rate_limited_api_v1_routes:
            wrapped = limiter.limit(limit_str, key_func=key_func)(func)
            self.add_url_rule(f"/api/v1/{route}", view_func=wrapped, methods=methods, endpoint=func.__name__)
        for route in monitoring_routes:
            self.add_url_rule(*route)

    @staticmethod
    def api_response(response: ServiceResponse):
        """Helper method to format API responses."""
        status = 200 if response["ok"] else ERROR_CODE_TO_HTTP.get(response["code"], 500)
        return jsonify(response), status

    def get_decks(self):
        data = self.service.get_decks()
        return self.api_response(data)

    def update_card_progress(self, card_id):
        result = request.args.get("result")

        if not result:
            return self.api_response(ErrorResponse("Parameter `result` is required", ErrorCode.VALIDATION_ERROR))

        data = self.service.update_card_progress(card_id, result)
        return self.api_response(data)

    def get_next_card(self, deck_id):
        data = self.service.get_next_card(deck_id)
        return self.api_response(data)

    def reset_progress(self, deck_id):
        data = self.service.reset_progress(deck_id)
        return self.api_response(data)

    def request_code(self):
        params = request.get_json()

        if not params.get("email"):
            return self.api_response(ErrorResponse("Parameter `email` is required", ErrorCode.VALIDATION_ERROR))

        email = params["email"].strip().lower()
        result = self.service.send_login_code(email)
        return self.api_response(result)

    def login(self):
        params = request.get_json()

        if not params.get("email") or not params.get("code"):
            return self.api_response(
                ErrorResponse("Parameters `email` and `code` are required", ErrorCode.VALIDATION_ERROR)
            )

        email, code = params["email"].strip().lower(), params["code"].strip()

        result = self.service.verify_login_code(email, code)
        if not result["ok"]:
            return self.api_response(result)

        user_data = result["data"]
        user = User(user_id=user_data["id"], email=user_data["email"])
        login_user(user)
        return self.api_response(SuccessResponse(message="Logged in successfully"))

    def logout(self):
        logout_user()
        return self.api_response(SuccessResponse(message="Logged out successfully"))

    @staticmethod
    @login_required
    def deck_page(*args, **kwargs):  # noqa
        return render_template("deck.html")

    @staticmethod
    def main_page():
        if not current_user.is_authenticated:
            return render_template("index.html")
        return render_template("decks.html")

    def health(self):
        service_health = self.service.health_check()
        if not service_health["ok"]:
            return "Service Unavailable", 500
        return "OK", 200

    @staticmethod
    def login_page():
        if current_user.is_authenticated:
            return redirect(url_for("main_page"))
        return render_template("login.html")

    @staticmethod
    def api_docs():
        return render_template("api_docs.html")


class AuthManager(LoginManager):
    def __init__(self, flask_app=None):
        super().__init__(flask_app)

        @self.user_loader
        def load_user(user_id, email=None):
            user = User(user_id, email)
            return user

        @self.unauthorized_handler
        def unauthorized():
            return render_template("unauthorized.html"), 401


def create_app(service=None):
    """Entry point for creating the Flask application."""

    flashcards_app = FlashcardsApp(service=service)
    flashcards_app.register_routes()

    login_manager = AuthManager()
    login_manager.init_app(flashcards_app)

    limiter.init_app(flashcards_app)

    return flashcards_app


if __name__ == "__main__":
    app = create_app(service=Service())
    app.run()
