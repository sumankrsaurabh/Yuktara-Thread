"""Consistent SQLite workspace backup and safe restore workflows."""
from __future__ import annotations

from contextlib import closing
from pathlib import Path
import os
import sqlite3
import tempfile

from yuktara_thread.infrastructure.database.migrations import MIGRATIONS


def _validate_database(path: Path) -> int:
    """Validate SQLite integrity, foreign keys and supported schema version."""
    connection = sqlite3.connect(path)
    try:
        integrity = connection.execute("PRAGMA integrity_check").fetchone()
        if integrity is None or integrity[0] != "ok":
            raise ValueError("Database integrity check failed")
        violations = connection.execute("PRAGMA foreign_key_check").fetchall()
        if violations:
            raise ValueError("Database contains foreign-key violations")
        table = connection.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='schema_migrations'"
        ).fetchone()
        if table is None:
            raise ValueError("File is not a Yuktara Thread workspace database")
        row = connection.execute(
            "SELECT COALESCE(MAX(version), 0) FROM schema_migrations"
        ).fetchone()
        version = int(row[0])
        latest = max(MIGRATIONS, default=0)
        if version < 1:
            raise ValueError("Workspace database has no applied schema migration")
        if version > latest:
            raise ValueError(
                f"Database schema version {version} is newer than supported version {latest}"
            )
        return version
    except sqlite3.DatabaseError as exc:
        raise ValueError(f"Invalid SQLite workspace database: {exc}") from exc
    finally:
        connection.close()


def _publish_new_file(temporary: Path, destination: Path) -> None:
    """Atomically publish a completed file without replacing an existing path."""
    try:
        os.link(temporary, destination)
    except FileExistsError:
        raise FileExistsError(f"Destination already exists: {destination}") from None
    temporary.unlink()


def _temporary_path(destination: Path) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    descriptor, name = tempfile.mkstemp(
        prefix=f".{destination.name}.", suffix=".tmp", dir=destination.parent
    )
    os.close(descriptor)
    return Path(name)


def backup_workspace(database_path: Path, output_path: Path) -> Path:
    """Create a consistent, integrity-checked SQLite snapshot without overwriting."""
    source = Path(database_path).resolve()
    destination = Path(output_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Workspace database not found: {source}")
    if source == destination:
        raise ValueError("Backup destination must differ from the workspace database")
    if destination.exists():
        raise FileExistsError(f"Backup destination already exists: {destination}")

    temporary = _temporary_path(destination)
    try:
        with closing(sqlite3.connect(source, timeout=10.0)) as origin:
            with closing(sqlite3.connect(temporary)) as target:
                origin.backup(target)
        _validate_database(temporary)
        _publish_new_file(temporary, destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()


def restore_workspace(backup_path: Path, database_path: Path) -> Path:
    """Restore a validated backup into a new database file without overwriting."""
    source = Path(backup_path).resolve()
    destination = Path(database_path).resolve()
    if not source.is_file():
        raise FileNotFoundError(f"Workspace backup not found: {source}")
    if source == destination:
        raise ValueError("Restore destination must differ from the backup file")
    if destination.exists():
        raise FileExistsError(f"Restore destination already exists: {destination}")

    _validate_database(source)
    temporary = _temporary_path(destination)
    try:
        with closing(sqlite3.connect(f"{source.as_uri()}?mode=ro", uri=True, timeout=10.0)) as origin:
            with closing(sqlite3.connect(temporary)) as target:
                origin.backup(target)
        _validate_database(temporary)
        _publish_new_file(temporary, destination)
        return destination
    finally:
        if temporary.exists():
            temporary.unlink()
