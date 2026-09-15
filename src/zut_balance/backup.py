import os
from datetime import UTC, datetime
from pathlib import Path
import sqlite3
import tempfile


def create_backup(database_path: Path, backup_directory: Path) -> Path:
    """Create an atomic, SQLite-consistent copy without interrupting the API."""
    if not database_path.is_file():
        raise FileNotFoundError(f"Database does not exist: {database_path}")

    backup_directory.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    destination = backup_directory / f"zut-balance-{timestamp}.sqlite3"
    if destination.exists():
        raise FileExistsError(f"Backup already exists: {destination}")
    with tempfile.NamedTemporaryFile(dir=backup_directory, prefix=".backup-", delete=False) as temporary:
        temporary_path = Path(temporary.name)
    try:
        with sqlite3.connect(database_path) as source, sqlite3.connect(temporary_path) as target:
            source.backup(target)
        os.replace(temporary_path, destination)
    except Exception:
        temporary_path.unlink(missing_ok=True)
        raise
    return destination


def main() -> None:
    database_path = os.environ.get("ZUT_BALANCE_DATABASE_PATH")
    backup_directory = os.environ.get("ZUT_BALANCE_BACKUP_DIRECTORY")
    if not database_path or not backup_directory:
        raise RuntimeError("ZUT_BALANCE_DATABASE_PATH and ZUT_BALANCE_BACKUP_DIRECTORY are required")
    print(create_backup(Path(database_path), Path(backup_directory)))


if __name__ == "__main__":
    main()
