from pathlib import Path
import pytest

from yuktara_thread.application.workspace import WorkspaceService


def test_workspace_migrates_and_creates_project(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("NovaUI", "Desktop UI framework")
    assert workspace.schema_version == 1
    assert project.name == "NovaUI"
    assert len(workspace.get_context(project.project_id)) == 6


def test_project_update_and_archive(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Initial")
    updated = workspace.update_project(project.project_id, "Renamed", "Summary")
    assert updated.name == "Renamed"
    archived = workspace.archive_project(project.project_id)
    assert archived.status == "archived"
    assert workspace.list_projects() == []
    assert len(workspace.list_projects(include_archived=True)) == 1


def test_context_revision_conflict_is_rejected(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Context test")
    first = next(s for s in workspace.get_context(project.project_id) if s.section_key == "goals")
    saved = workspace.save_context(
        project.project_id, "goals", "Ship a reliable MVP", expected_revision=first.revision
    )
    assert saved.revision == first.revision + 1
    with pytest.raises(RuntimeError, match="changed since it was opened"):
        workspace.save_context(
            project.project_id, "goals", "Stale write", expected_revision=first.revision
        )
    history = workspace.context.history(project.project_id, "goals")
    assert history[0]["content"] == "Ship a reliable MVP"


def test_invalid_project_name_is_rejected(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    with pytest.raises(ValueError):
        workspace.create_project("   ")
