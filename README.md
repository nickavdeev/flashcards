# Flashcards App

Simple flashcard application for learning and memorization. Set up the app, create decks, and review cards.

## Tech stack

Minimal Flask UI + a JSON API.

- **Backend:** Flask
- **Database:** SQLite (via the standard `sqlite3` module, no ORM)
- **Package management:** [uv](https://docs.astral.sh/uv/)
- **Linting:** [ruff](https://docs.astral.sh/ruff/)
- **Testing:** unittest

## Architecture

The app is split into three independent layers:

```
app.py            → Flask layer: routes, request/response handling, HTML pages
service/          → business logic: validation, orchestration, response formatting
database/         → data access: raw SQL queries to the SQLite database
```

Each layer only talks to the one directly below it (`app` → `service` → `database`), and each is tested in isolation — the database layer runs real queries against an in-memory SQLite database, the service layer is tested with the database mocked out, and the Flask layer is tested with the service mocked out.

## Installation

1. Clone this repository:
   ```bash
   git clone https://github.com/nickavdeev/flashcards.git
   cd flashcards
   ```
2. Create a `.env` file in the root of the project and fill it with the variables from `.env.example`:
   ```bash
   cp .env.example .env
   ```
3. Install dependencies using uv:
   ```bash
   uv sync
   ```
4. Install JS tooling dependencies:
   ```bash
    npm install
   ```

## Running the app

```bash
uv run python app.py
```

By default the app is served at `http://localhost:5000`.

## API

All API routes are prefixed with `/api/v1`.

| Method | Endpoint                          | Description                                 |
| ------ | --------------------------------- | ------------------------------------------- |
| GET    | `/decks`                          | List all decks                              |
| GET    | `/deck/<deck_id>/cards/next`      | Get the next card due for review in a deck  |
| POST   | `/cards/<card_id>/review?result=` | Submit a review result (`know` or `revise`) |
| POST   | `/deck/<deck_id>/reset`           | Reset review progress for a deck            |
| GET    | `/health`                         | Health check, verifies the Service health   |

Page routes (`/`, `/deck/<deck_id>`) serve the HTML UI.

## Running tests

Tests live in the `tests/` directory and mirror the project's layers (`test_database.py`, `test_service.py`, `test_app.py`).

```bash
uv run python -m unittest discover -s tests -p "test_*.py" -v
```

## Running linters
 
Python:
```bash
uv run ruff check --fix
```
 
JS and HTML:
```bash
npx prettier --check static/ templates/
npx prettier --write static/ templates/
```
