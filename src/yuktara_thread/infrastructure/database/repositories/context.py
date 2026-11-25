"""Repository for structured context sections and revision history."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4

from yuktara_thread.domain.context.models import CONTEXT_TITLES, ContextSection
from yuktara_thread.infrastructure.database.connection import Database
from yuktara_thread.infrastructure.database.repositories.events import append_project_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ContextRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def ensure_default_sections(self, project_id: str) -> None:
        now = _now()
        with self.database.transaction() as connection:
            exists = connection.execute(
                "SELECT 1 FROM projects WHERE project_id = ?", (project_id,)
            ).fetchone()
            if not exists:
                raise LookupError("Project not found")
            for key, title in CONTEXT_TITLES.items():
                connection.execute(
                    """INSERT OR IGNORE INTO context_sections
                       (section_id, project_id, section_key, title, content, revision, updated_at)
                       VALUES (?, ?, ?, ?, '', 1, ?)""",
                    (str(uuid4()), project_id, key, title, now),
                )
                section = connection.execute(
                    "SELECT section_id, title, content, revision FROM context_sections "
                    "WHERE project_id = ? AND section_key = ?", (project_id, key)
                ).fetchone()
                connection.execute(
                    """INSERT OR IGNORE INTO context_revisions
                       (revision_id, section_id, revision, title, content, created_at)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (str(uuid4()), section["section_id"], section["revision"],
                     section["title"], section["content"], now),
                )

    def list_for_project(self, project_id: str) -> list[ContextSection]:
        with self.database.read() as connection:
            rows = connection.execute(
                "SELECT * FROM context_sections WHERE project_id = ? ORDER BY section_key",
                (project_id,),
            ).fetchall()
        return [ContextSection(**dict(row)) for row in rows]

    def save(
        self, project_id: str, section_key: str, content: str, *,
        expected_revision: int,
    ) -> ContextSection:
        if section_key not in CONTEXT_TITLES:
            raise ValueError(f"Unsupported context section: {section_key}")
        if len(content) > 200_000:
            raise ValueError("Context section exceeds 200,000 characters")
        now = _now()
        with self.database.transaction() as connection:
            row = connection.execute(
                "SELECT * FROM context_sections WHERE project_id = ? AND section_key = ?",
                (project_id, section_key),
            ).fetchone()
            if row is None:
                raise LookupError("Context section not found; initialize project sections first")
            if row["revision"] != expected_revision:
                raise RuntimeError(
                    f"Context changed since it was opened (expected revision {expected_revision}, "
                    f"current revision {row['revision']})"
                )
            new_revision = expected_revision + 1
            cursor = connection.execute(
                """UPDATE context_sections SET content = ?, revision = ?, updated_at = ?
                   WHERE section_id = ? AND revision = ?""",
                (content, new_revision, now, row["section_id"], expected_revision),
            )
            if cursor.rowcount != 1:
                raise RuntimeError("Context was modified by another operation; reload and retry")
            connection.execute(
                """INSERT INTO context_revisions
                   (revision_id, section_id, revision, title, content, created_at)
                   VALUES (?, ?, ?, ?, ?, ?)""",
                (str(uuid4()), row["section_id"], new_revision, row["title"], content, now),
            )
            append_project_event(connection, project_id=project_id, event_type="context.updated",
                entity_type="context_section", entity_id=row["section_id"],
                payload={"section_key": section_key, "revision": new_revision}, created_at=now)
            updated = connection.execute(
                "SELECT * FROM context_sections WHERE section_id = ?", (row["section_id"],)
            ).fetchone()
        return ContextSection(**dict(updated))

    def history(self, project_id: str, section_key: str) -> list[dict[str, object]]:
        with self.database.read() as connection:
            rows = connection.execute(
                """SELECT r.revision, r.title, r.content, r.created_at
                   FROM context_revisions r
                   JOIN context_sections s ON s.section_id = r.section_id
                   WHERE s.project_id = ? AND s.section_key = ?
                   ORDER BY r.revision DESC""",
                (project_id, section_key),
            ).fetchall()
        return [dict(row) for row in rows]
