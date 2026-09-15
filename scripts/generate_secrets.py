#!/usr/bin/env python3
import argparse
import getpass
import secrets

from argon2 import PasswordHasher


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate Zut Balance deployment secrets")
    parser.add_argument("kind", choices=("password-hash", "session-secret", "api-key"))
    arguments = parser.parse_args()
    if arguments.kind == "password-hash":
        password = getpass.getpass("Administrator password: ")
        if not password:
            raise SystemExit("Password cannot be empty")
        print(f"'{PasswordHasher().hash(password)}'")
    elif arguments.kind == "session-secret":
        print(secrets.token_urlsafe(48))
    else:
        print(secrets.token_urlsafe(32))


if __name__ == "__main__":
    main()
