"""Authentication helpers for web sessions and integration API keys."""

from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError


_PASSWORD_HASHER = PasswordHasher()
MINIMUM_SESSION_SECRET_LENGTH = 32


class AuthenticationConfigurationError(RuntimeError):
    """Raised when the configured web authentication secrets are unsafe."""


def validate_web_authentication_settings(
    password_hash: str | None, session_secret: str | None, trusted_origins: tuple[str, ...]
) -> None:
    """Reject incomplete web session configuration before serving data."""
    if not password_hash or not session_secret or not trusted_origins:
        raise AuthenticationConfigurationError("Web authentication is not configured")
    if len(session_secret) < MINIMUM_SESSION_SECRET_LENGTH:
        raise AuthenticationConfigurationError("The session secret is too short")
    try:
        _PASSWORD_HASHER.check_needs_rehash(password_hash)
    except InvalidHashError as error:
        raise AuthenticationConfigurationError("The administrator password hash is invalid") from error


def verify_administrator_password(password_hash: str, password: str) -> bool:
    """Verify a supplied administrator password without exposing hash details."""
    try:
        return _PASSWORD_HASHER.verify(password_hash, password)
    except (InvalidHashError, VerificationError):
        return False
