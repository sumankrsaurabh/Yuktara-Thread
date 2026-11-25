"""Ordered, transactional SQLite schema migrations.

Each migration is a list of individual statements. Avoid executescript() here:
sqlite3.executescript() may implicitly commit and break migration atomicity.
"""
from __future__ import annotations

import sqlite3

MIGRATIONS: dict[int, tuple[str, ...]] = {
    1: (
        """CREATE TABLE projects (
            project_id TEXT PRIMARY KEY,
            name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            summary TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'active'
                CHECK(status IN ('active', 'archived')),
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL,
            archived_at TEXT
        )""",
        """CREATE INDEX idx_projects_status_updated
            ON projects(status, updated_at DESC)""",
        """CREATE TABLE context_sections (
            section_id TEXT PRIMARY KEY,
            project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            section_key TEXT NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL DEFAULT '',
            revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0),
            updated_at TEXT NOT NULL,
            UNIQUE(project_id, section_key)
        )""",
        """CREATE TABLE context_revisions (
            revision_id TEXT PRIMARY KEY,
            section_id TEXT NOT NULL REFERENCES context_sections(section_id) ON DELETE CASCADE,
            revision INTEGER NOT NULL,
            title TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TEXT NOT NULL,
            UNIQUE(section_id, revision)
        )""",
        """CREATE INDEX idx_context_revisions_section
            ON context_revisions(section_id, revision DESC)""",
    ),
}


def apply_migrations(connection: sqlite3.Connection) -> int:
    """Apply pending migrations and return the current schema version."""
    connection.execute(
        """CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            applied_at TEXT NOT NULL
        )"""
    )
    row = connection.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
    current = int(row["version"])
    for version in sorted(MIGRATIONS):
        if version <= current:
            continue
        if version != current + 1:
            raise RuntimeError(f"Missing migration after schema version {current}")
        # The caller must invoke this inside Database.transaction().
        for statement in MIGRATIONS[version]:
            connection.execute(statement)
        from datetime import datetime, timezone
        connection.execute(
            "INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
            (version, datetime.now(timezone.utc).isoformat()),
        )
        current = version
    return current
