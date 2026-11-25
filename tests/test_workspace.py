from pathlib import Path
import sqlite3
import pytest
from yuktara_thread.application.workspace import WorkspaceService

def test_workspace_migrates_and_creates_project(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("NovaUI", "Desktop UI framework")
    assert workspace.schema_version == 2
    assert project.name == "NovaUI"
    assert len(workspace.get_context(project.project_id)) == 6
    initial = workspace.context.history(project.project_id, "goals")
    assert len(initial) == 1 and initial[0]["revision"] == 1

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
    saved = workspace.save_context(project.project_id, "goals", "Ship a reliable MVP",
                                   expected_revision=first.revision)
    assert saved.revision == first.revision + 1
    with pytest.raises(RuntimeError, match="changed since it was opened"):
        workspace.save_context(project.project_id, "goals", "Stale write",
                               expected_revision=first.revision)
    history = workspace.context.history(project.project_id, "goals")
    assert [item["revision"] for item in history] == [2, 1]
    assert history[0]["content"] == "Ship a reliable MVP"

def test_invalid_project_name_is_rejected(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    with pytest.raises(ValueError):
        workspace.create_project("   ")

def test_newer_database_schema_is_rejected(tmp_path: Path) -> None:
    path = tmp_path / "future.sqlite3"
    connection = sqlite3.connect(path)
    connection.execute("CREATE TABLE schema_migrations (version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL)")
    connection.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (999, 'future')")
    connection.commit()
    connection.close()
    with pytest.raises(RuntimeError, match="newer than this application supports"):
        WorkspaceService(path)


def test_workspace_export_preserves_context_intelligence_and_dependencies(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import export_workspace_project
    from yuktara_thread.infrastructure.package import preview_package

    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Exported project", "A complete handover")
    goals = next(section for section in workspace.get_context(project.project_id)
                 if section.section_key == "goals")
    workspace.save_context(project.project_id, "goals", "Ship the first release",
                           expected_revision=goals.revision)
    workspace.intelligence.create_decision(
        project.project_id, title="Use SQLite", rationale="Local-first persistence"
    )
    prerequisite = workspace.intelligence.create_task(
        project.project_id, title="Design schema"
    )
    dependent = workspace.intelligence.create_task(
        project.project_id, title="Implement repository"
    )
    workspace.intelligence.add_task_dependency(
        project.project_id, dependent["task_id"], prerequisite["task_id"]
    )
    workspace.intelligence.create_milestone(project.project_id, title="MVP")
    workspace.intelligence.create_reference(
        project.project_id, title="Architecture notes", uri="docs/architecture.md"
    )
    files = tmp_path / "selected-files"
    files.mkdir()
    (files / "README.md").write_text("Project instructions", encoding="utf-8")

    package = export_workspace_project(
        workspace, project.project_id, files, tmp_path / "project.thread"
    )
    preview = preview_package(package)
    payload = preview["project"]

    assert payload["name"] == "Exported project"
    assert len(payload["context_sections"]) == 6
    assert next(s for s in payload["context_sections"] if s["section_key"] == "goals")["content"] == "Ship the first release"
    assert len(payload["decisions"]) == 1
    assert len(payload["tasks"]) == 2
    assert len(payload["milestones"]) == 1
    assert len(payload["references"]) == 1
    assert payload["task_dependencies"] == [{
        "task_id": dependent["task_id"],
        "depends_on_task_id": prerequisite["task_id"],
    }]
    assert payload["activity_events"]
    assert [item["path"] for item in preview["files"]] == ["README.md"]


def test_workspace_export_rejects_archived_project(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import export_workspace_project

    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Archived")
    workspace.archive_project(project.project_id)
    files = tmp_path / "files"
    files.mkdir()

    with pytest.raises(ValueError, match="Archived projects"):
        export_workspace_project(workspace, project.project_id, files, tmp_path / "archived.thread")
