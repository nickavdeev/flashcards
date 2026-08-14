import hashlib
import secrets


class LoginService:
    """Service for handling login operations, including code generation and verification."""

    CODE_TTL_MINUTES = 5  # Time-to-live for login codes in minutes
    MAX_ATTEMPTS = 5  # Maximum number of attempts for code verification

    @staticmethod
    def _generate_code() -> str:
        return f"{secrets.randbelow(1_000_000):06d}"

    @staticmethod
    def _hash_code(code: str, email: str) -> str:
        return hashlib.sha256(f"{email}:{code}".encode()).hexdigest()
