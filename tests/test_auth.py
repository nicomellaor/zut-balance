from argon2 import PasswordHasher
import pytest

from zut_balance.api import ServiceSettings, create_app
from zut_balance.auth import (
    AuthenticationConfigurationError,
    verify_administrator_password,
    validate_web_authentication_settings,
)


def test_web_authentication_settings_require_valid_secrets() -> None:
    password_hash = PasswordHasher().hash("admin-password")

    validate_web_authentication_settings(password_hash, "s" * 32, ("https://zut.test",))

    with pytest.raises(AuthenticationConfigurationError):
        validate_web_authentication_settings(None, "s" * 32, ("https://zut.test",))
    with pytest.raises(AuthenticationConfigurationError):
        validate_web_authentication_settings(password_hash, "short", ("https://zut.test",))
    with pytest.raises(AuthenticationConfigurationError):
        validate_web_authentication_settings("not-a-hash", "s" * 32, ("https://zut.test",))


def test_password_verification_hides_invalid_hashes_and_passwords() -> None:
    password_hash = PasswordHasher().hash("admin-password")

    assert verify_administrator_password(password_hash, "admin-password") is True
    assert verify_administrator_password(password_hash, "wrong-password") is False
    assert verify_administrator_password("invalid", "admin-password") is False


def test_web_authentication_requires_an_integration_key(tmp_path) -> None:
    password_hash = PasswordHasher().hash("admin-password")

    with pytest.raises(RuntimeError, match="integration API key"):
        create_app(
            ServiceSettings(
                tmp_path / "statements.sqlite3",
                None,
                web_auth_enabled=True,
                admin_password_hash=password_hash,
                session_secret="s" * 32,
                trusted_origins=("https://zut.test",),
            )
        )
