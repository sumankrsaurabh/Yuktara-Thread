"""Project repository backed by SQLite."""
from __future__ import annotations
from datetime import datetime, timezone
from uuid import uuid4

from yuktara_thread.domain.projects.models import Project, validate_project_name
from yuktara_thread.infrastructure.database.connection import Database
from yuktara_thread.infrastructure.database.repositories.events import append_project_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectRepository:
    def __init__(self, database: Database) -> None:
        self.database = database

    def create(self, name: str, summary: str = "") -> Project:
        project_id, now = str(uuid4()), _now()
        clean_name = validate_project_name(name)
        clean_summary = summary.strip()
        with self.database.transaction() as connection:
            connection.execute(
                """INSERT INTO projects(project_id, name, summary, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'active', ?, ?)""",
                (project_id, clean_name, clean_summary, now, now),
            )
            append_project_event(connection, project_id=project_id, event_type="project.created",
                entity_type="project", entity_id=project_id,
                payload={"name": clean_name}, created_at=now)
            row = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return Project.from_row(row)

    def get(self, project_id: str) -> Project | None:
        with self.database.read() as connection:
            row = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return Project.from_row(row) if row else None

    def list(self, include_archived: bool = False) -> list[Project]:
        query = "SELECT * FROM projects"
        if not include_archived:
            query += " WHERE status = 'active'"
        query += " ORDER BY updated_at DESC, name COLLATE NOCASE"
        with self.database.read() as connection:
            rows = connection.execute(query).fetchall()
        return [Project.from_row(row) for row in rows]

    def update(self, project_id: str, *, name: str, summary: str) -> Project:
        now = _now()
        clean_name, clean_summary = validate_project_name(name), summary.strip()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE projects SET name = ?, summary = ?, updated_at = ?
                   WHERE project_id = ? AND status = 'active'""",
                (clean_name, clean_summary, now, project_id),
            )
            if cursor.rowcount != 1:
                raise LookupError("Active project not found")
            append_project_event(connection, project_id=project_id, event_type="project.updated",
                entity_type="project", entity_id=project_id,
                payload={"name": clean_name, "summary_changed": True}, created_at=now)
            row = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return Project.from_row(row)

    def archive(self, project_id: str) -> Project:
        now = _now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE projects SET status = 'archived', archived_at = ?, updated_at = ?
                   WHERE project_id = ? AND status = 'active'""",
                (now, now, project_id),
            )
            if cursor.rowcount != 1:
                raise LookupError("Active project not found")
            append_project_event(connection, project_id=project_id, event_type="project.archived",
                entity_type="project", entity_id=project_id, payload={}, created_at=now)
            row = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return Project.from_row(row)

    def restore(self, project_id: str) -> Project:
        """Restore an archived project without changing its records or history."""
        now = _now()
        with self.database.transaction() as connection:
            cursor = connection.execute(
                """UPDATE projects SET status = 'active', archived_at = NULL, updated_at = ?
                   WHERE project_id = ? AND status = 'archived'""",
                (now, project_id),
            )
            if cursor.rowcount != 1:
                raise LookupError("Archived project not found")
            append_project_event(connection, project_id=project_id, event_type="project.restored",
                entity_type="project", entity_id=project_id, payload={}, created_at=now)
            row = connection.execute("SELECT * FROM projects WHERE project_id = ?", (project_id,)).fetchone()
        return Project.from_row(row)
