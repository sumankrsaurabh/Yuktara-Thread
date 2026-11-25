from pathlib import Path

import pytest

from yuktara_thread.application.backup import backup_workspace, restore_workspace
from yuktara_thread.application.workspace import WorkspaceService


def test_workspace_backup_and_restore_round_trip_consistent_snapshot(tmp_path: Path) -> None:
    database = tmp_path / "workspace.sqlite3"
    workspace = WorkspaceService(database)
    project = workspace.create_project("Before backup", "Original summary")
    backup = backup_workspace(database, tmp_path / "snapshots" / "workspace.backup")

    workspace.update_project(project.project_id, "After backup", "Changed later")
    restored_path = restore_workspace(backup, tmp_path / "restored" / "workspace.sqlite3")
    restored = WorkspaceService(restored_path)
    projects = restored.list_projects()

    assert len(projects) == 1
    assert projects[0].name == "Before backup"
    assert projects[0].summary == "Original summary"
    assert len(restored.get_context(project.project_id)) == 6


def test_backup_and_restore_never_overwrite_existing_files(tmp_path: Path) -> None:
    database = tmp_path / "workspace.sqlite3"
    WorkspaceService(database)
    backup = tmp_path / "workspace.backup"
    backup_workspace(database, backup)

    with pytest.raises(FileExistsError, match="already exists"):
        backup_workspace(database, backup)

    destination = tmp_path / "restored.sqlite3"
    destination.write_text("keep this file", encoding="utf-8")
    with pytest.raises(FileExistsError, match="already exists"):
        restore_workspace(backup, destination)
    assert destination.read_text(encoding="utf-8") == "keep this file"


def test_restore_rejects_non_workspace_or_corrupt_database(tmp_path: Path) -> None:
    invalid = tmp_path / "not-a-workspace.sqlite3"
    invalid.write_text("not a database", encoding="utf-8")

    with pytest.raises(ValueError, match="Invalid SQLite|workspace database"):
        restore_workspace(invalid, tmp_path / "restored.sqlite3")

    assert not (tmp_path / "restored.sqlite3").exists()


def test_backup_requires_existing_workspace_database(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        backup_workspace(tmp_path / "missing.sqlite3", tmp_path / "backup.sqlite3")
