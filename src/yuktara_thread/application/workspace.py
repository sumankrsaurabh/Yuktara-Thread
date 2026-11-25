"""Workspace application service: coordinates database, migrations and repositories."""
from __future__ import annotations
from pathlib import Path

from yuktara_thread.domain.context.models import ContextSection
from yuktara_thread.domain.projects.models import Project
from yuktara_thread.infrastructure.database.connection import Database
from yuktara_thread.infrastructure.database.migrations import apply_migrations
from yuktara_thread.infrastructure.database.repositories.context import ContextRepository
from yuktara_thread.infrastructure.database.repositories.projects import ProjectRepository
from yuktara_thread.infrastructure.database.repositories.intelligence import ProjectIntelligenceRepository


class WorkspaceService:
    """Application boundary for local workspace operations."""

    def __init__(self, database_path: Path) -> None:
        self.database = Database(database_path)
        with self.database.transaction() as connection:
            self.schema_version = apply_migrations(connection)
        self.projects = ProjectRepository(self.database)
        self.context = ContextRepository(self.database)
        self.intelligence = ProjectIntelligenceRepository(self.database)

    def create_project(self, name: str, summary: str = "") -> Project:
        project = self.projects.create(name, summary)
        self.context.ensure_default_sections(project.project_id)
        return project

    def list_projects(self, include_archived: bool = False) -> list[Project]:
        return self.projects.list(include_archived=include_archived)

    def update_project(self, project_id: str, name: str, summary: str) -> Project:
        return self.projects.update(project_id, name=name, summary=summary)

    def archive_project(self, project_id: str) -> Project:
        return self.projects.archive(project_id)

    def restore_project(self, project_id: str) -> Project:
        """Restore an archived project and preserve its existing workspace data."""
        return self.projects.restore(project_id)

    def get_context(self, project_id: str) -> list[ContextSection]:
        return self.context.list_for_project(project_id)

    def save_context(self, project_id: str, section_key: str, content: str, *,
                     expected_revision: int) -> ContextSection:
        return self.context.save(project_id, section_key, content, expected_revision=expected_revision)
