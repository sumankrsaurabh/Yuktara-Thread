from pathlib import Path
import sqlite3
import pytest
from yuktara_thread.application.workspace import WorkspaceService

def test_workspace_migrates_and_creates_project(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("NovaUI", "Desktop UI framework")
    assert workspace.schema_version == 4
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
    assert payload["handover_readiness"]["status"] == "incomplete"
    assert payload["handover_readiness"]["score"] < 100
    assert len(payload["context_sections"]) == 6
    assert next(s for s in payload["context_sections"] if s["section_key"] == "goals")["content"] == "Ship the first release"
    assert [item["revision"] for item in payload["context_history"]["goals"]] == [2, 1]
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


def test_workspace_import_restores_context_records_dependencies_and_files(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import (
        export_workspace_project, import_workspace_project,
    )

    source_workspace = WorkspaceService(tmp_path / "source.sqlite3")
    source_project = source_workspace.create_project("Portable project", "Transfer this")
    goals = next(section for section in source_workspace.get_context(source_project.project_id)
                 if section.section_key == "goals")
    source_workspace.save_context(
        source_project.project_id, "goals", "Preserve the reasoning",
        expected_revision=goals.revision,
    )
    source_workspace.intelligence.create_decision(
        source_project.project_id, title="Use SQLite", alternatives=["JSON", "SQLite"],
        rationale="Transactions",
    )
    prerequisite = source_workspace.intelligence.create_task(
        source_project.project_id, title="Design schema"
    )
    dependent = source_workspace.intelligence.create_task(
        source_project.project_id, title="Implement storage"
    )
    source_workspace.intelligence.add_task_dependency(
        source_project.project_id, dependent["task_id"], prerequisite["task_id"]
    )
    source_workspace.intelligence.create_milestone(
        source_project.project_id, title="First release"
    )
    source_workspace.intelligence.create_reference(
        source_project.project_id, title="Design notes", uri="docs/design.md"
    )
    selected = tmp_path / "selected-files"
    selected.mkdir()
    (selected / "README.md").write_text("Portable instructions", encoding="utf-8")
    package = export_workspace_project(
        source_workspace, source_project.project_id, selected, tmp_path / "portable.thread"
    )

    receiving_workspace = WorkspaceService(tmp_path / "receiving.sqlite3")
    imported, extracted = import_workspace_project(
        receiving_workspace, package, tmp_path / "received-files"
    )

    assert imported.name == "Portable project"
    with receiving_workspace.database.read() as connection:
        journal = connection.execute(
            "SELECT status, project_id FROM handover_imports"
        ).fetchone()
    assert journal["status"] == "completed"
    assert journal["project_id"] == imported.project_id
    assert imported.project_id != source_project.project_id
    assert (extracted / "files" / "README.md").read_text(encoding="utf-8") == "Portable instructions"
    context = {section.section_key: section.content for section in receiving_workspace.get_context(imported.project_id)}
    assert context["goals"] == "Preserve the reasoning"
    restored_goals = next(
        section for section in receiving_workspace.get_context(imported.project_id)
        if section.section_key == "goals"
    )
    assert restored_goals.revision == 2
    restored_history = receiving_workspace.context.history(imported.project_id, "goals")
    assert [item["revision"] for item in restored_history] == [2, 1]
    assert restored_history[1]["content"] == ""
    decisions = receiving_workspace.intelligence.list_records(imported.project_id, "decision")
    assert decisions[0]["alternatives"] == ["JSON", "SQLite"]
    tasks = receiving_workspace.intelligence.list_records(imported.project_id, "task")
    task_by_title = {task["title"]: task for task in tasks}
    assert receiving_workspace.intelligence.list_task_dependencies(
        task_by_title["Implement storage"]["task_id"]
    ) == [task_by_title["Design schema"]["task_id"]]
    assert len(receiving_workspace.intelligence.list_records(imported.project_id, "milestone")) == 1
    assert len(receiving_workspace.intelligence.list_records(imported.project_id, "reference")) == 1
    imported_events = receiving_workspace.intelligence.timeline(imported.project_id, limit=1000)
    assert "handover.imported" in {event["event_type"] for event in imported_events}
    source_task_events = [
        event for event in imported_events
        if event["event_type"] == "task.created"
        and event["payload"].get("_origin") == "imported"
    ]
    assert len(source_task_events) == 2
    assert source_task_events[0]["payload"]["title"] in {
        "Design schema", "Implement storage"
    }


def test_import_reconciliation_preserves_orphaned_files_for_manual_review(
    tmp_path: Path,
) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4
    from yuktara_thread.application.handover import reconcile_workspace_imports

    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    destination = tmp_path / "orphaned-files"
    destination.mkdir()
    (destination / "README.md").write_text("Keep for review", encoding="utf-8")
    now = datetime.now(timezone.utc).isoformat()
    import_id = str(uuid4())
    project_id = str(uuid4())
    with workspace.database.transaction() as connection:
        connection.execute(
            """INSERT INTO handover_imports
               (import_id, project_id, package_manifest_sha256, destination_path,
                status, phase, error, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'files_ready', 'files_ready', NULL, ?, ?)""",
            (import_id, project_id, "a" * 64, str(destination), now, now),
        )

    result = reconcile_workspace_imports(workspace)

    assert len(result) == 1
    assert result[0]["status"] == "recovery_required"
    assert result[0]["project_present"] is False
    assert result[0]["files_present"] is True
    assert destination.joinpath("README.md").read_text(encoding="utf-8") == "Keep for review"
    assert result[0]["error"]


def test_import_reconciliation_marks_committed_project_complete(tmp_path: Path) -> None:
    from datetime import datetime, timezone
    from uuid import uuid4
    from yuktara_thread.application.handover import reconcile_workspace_imports

    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Committed project")
    destination = tmp_path / "committed-files"
    destination.mkdir()
    now = datetime.now(timezone.utc).isoformat()
    import_id = str(uuid4())
    with workspace.database.transaction() as connection:
        connection.execute(
            """INSERT INTO handover_imports
               (import_id, project_id, package_manifest_sha256, destination_path,
                status, phase, error, created_at, updated_at)
               VALUES (?, ?, ?, ?, 'database_committed', 'database_committed', NULL, ?, ?)""",
            (import_id, project.project_id, "b" * 64, str(destination), now, now),
        )

    result = reconcile_workspace_imports(workspace)

    assert result[0]["status"] == "completed"
    assert result[0]["project_present"] is True
    assert result[0]["files_present"] is True
    with workspace.database.read() as connection:
        status = connection.execute(
            "SELECT status FROM handover_imports WHERE import_id = ?", (import_id,)
        ).fetchone()["status"]
    assert status == "completed"


def test_workspace_import_rejects_dependency_cycle_before_extracting(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import import_workspace_project
    from yuktara_thread.domain.models import ProjectContext
    from yuktara_thread.infrastructure.package import create_package

    package_source = tmp_path / "empty"
    package_source.mkdir()
    first_id, second_id = "task-one", "task-two"
    payload = {
        **ProjectContext.create("Cyclic package").to_dict(),
        "handover_schema_version": 1,
        "tasks": [
            {"task_id": first_id, "title": "One"},
            {"task_id": second_id, "title": "Two"},
        ],
        "task_dependencies": [
            {"task_id": first_id, "depends_on_task_id": second_id},
            {"task_id": second_id, "depends_on_task_id": first_id},
        ],
    }
    package = tmp_path / "cycle.thread"
    create_package(package_source, package, payload)
    workspace = WorkspaceService(tmp_path / "receiving.sqlite3")
    destination = tmp_path / "must-not-exist"

    with pytest.raises(ValueError, match="dependency cycle"):
        import_workspace_project(workspace, package, destination)

    assert workspace.list_projects() == []
    assert not destination.exists()


def test_workspace_import_removes_extracted_files_when_database_transaction_fails(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import import_workspace_project
    from yuktara_thread.domain.models import ProjectContext
    from yuktara_thread.infrastructure.package import create_package

    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("Rollback test", encoding="utf-8")
    package = tmp_path / "rollback.thread"
    create_package(source, package, ProjectContext.create("Rollback project").to_dict())
    workspace = WorkspaceService(tmp_path / "receiving.sqlite3")
    with workspace.database.transaction() as connection:
        connection.execute(
            """CREATE TRIGGER reject_handover_project
               BEFORE INSERT ON projects
               BEGIN SELECT RAISE(ABORT, 'simulated database failure'); END;"""
        )
    destination = tmp_path / "extracted"

    with pytest.raises(RuntimeError, match="simulated database failure"):
        import_workspace_project(workspace, package, destination)

    assert workspace.list_projects() == []
    assert not destination.exists()


def test_workspace_import_reports_manual_recovery_when_file_cleanup_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    from yuktara_thread.application import handover
    from yuktara_thread.application.handover import import_workspace_project
    from yuktara_thread.domain.models import ProjectContext
    from yuktara_thread.infrastructure.package import create_package

    source = tmp_path / "source"
    source.mkdir()
    (source / "README.md").write_text("Recovery guidance", encoding="utf-8")
    package = tmp_path / "recovery.thread"
    create_package(source, package, ProjectContext.create("Recovery project").to_dict())
    workspace = WorkspaceService(tmp_path / "receiving.sqlite3")
    with workspace.database.transaction() as connection:
        connection.execute(
            """CREATE TRIGGER reject_handover_project
               BEFORE INSERT ON projects
               BEGIN SELECT RAISE(ABORT, 'simulated database failure'); END;"""
        )
    destination = tmp_path / "recovery-files"
    real_rmtree = handover.shutil.rmtree

    def retain_directory(path, *args, **kwargs):
        if Path(path) == destination:
            raise OSError("simulated cleanup failure")
        return real_rmtree(path, *args, **kwargs)

    monkeypatch.setattr(handover.shutil, "rmtree", retain_directory)

    with pytest.raises(RuntimeError, match="could not be removed automatically") as error:
        import_workspace_project(workspace, package, destination)

    assert error.value.phase == "database_transaction"
    assert error.value.recovery_path == destination
    assert destination.exists()
    assert "After confirming no project was created" in str(error.value)
    assert workspace.list_projects() == []


def test_archived_project_can_be_restored_without_losing_data_or_history(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Recoverable project", "Keep this summary")
    task = workspace.intelligence.create_task(project.project_id, title="Preserve this task")
    workspace.archive_project(project.project_id)

    restored = workspace.restore_project(project.project_id)

    assert restored.status == "active"
    assert restored.archived_at is None
    assert restored.name == "Recoverable project"
    assert restored.summary == "Keep this summary"
    assert workspace.list_projects()[0].project_id == project.project_id
    assert workspace.intelligence.list_records(project.project_id, "task")[0]["task_id"] == task["task_id"]
    event_types = [event["event_type"] for event in workspace.intelligence.timeline(project.project_id)]
    assert "project.archived" in event_types
    assert "project.restored" in event_types


def test_only_archived_projects_can_be_restored(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = workspace.create_project("Already active")
    with pytest.raises(LookupError, match="Archived project not found"):
        workspace.restore_project(project.project_id)


def test_handover_import_inspection_reports_name_and_record_collisions_without_mutation(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import (
        export_workspace_project, inspect_workspace_import,
    )

    source_workspace = WorkspaceService(tmp_path / "source.sqlite3")
    source_project = source_workspace.create_project("Shared project")
    source_workspace.intelligence.create_task(
        source_project.project_id, title="Implement storage"
    )
    selected_files = tmp_path / "selected"
    selected_files.mkdir()
    package = export_workspace_project(
        source_workspace, source_project.project_id, selected_files,
        tmp_path / "shared.thread",
    )

    destination_workspace = WorkspaceService(tmp_path / "destination.sqlite3")
    existing = destination_workspace.create_project("shared PROJECT")
    goals = next(
        section for section in destination_workspace.get_context(existing.project_id)
        if section.section_key == "goals"
    )
    destination_workspace.save_context(
        existing.project_id, "goals", "A different local goal",
        expected_revision=goals.revision,
    )
    destination_workspace.intelligence.create_task(
        existing.project_id, title="Implement storage"
    )

    inspection = inspect_workspace_import(destination_workspace, package)

    assert inspection["valid"] is True
    assert inspection["has_conflicts"] is True
    assert inspection["recommended_action"] == "review_before_import"
    assert inspection["candidate_projects"] == [{
        "project_id": existing.project_id,
        "name": "shared PROJECT",
        "status": "active",
        "match_reason": "project_name",
    }]
    assert inspection["record_collisions"] == [{
        "project_id": existing.project_id,
        "project_name": "shared PROJECT",
        "entity_type": "task",
        "titles": ["Implement storage"],
    }]
    comparison = inspection["comparisons"][0]
    assert comparison["project_summary_differs"] is False
    assert comparison["context_differences"] == [{
        "section_key": "goals",
        "change": "content_differs",
        "source_revision": 1,
        "destination_revision": 2,
    }]
    assert comparison["source_counts"]["task"] == 1
    assert comparison["destination_counts"]["task"] == 1
    assert len(destination_workspace.list_projects(include_archived=True)) == 1
    assert len(destination_workspace.intelligence.list_records(existing.project_id, "task")) == 1


def test_handover_import_inspection_recommends_new_project_when_no_match(tmp_path: Path) -> None:
    from yuktara_thread.application.handover import (
        export_workspace_project, inspect_workspace_import,
    )

    source_workspace = WorkspaceService(tmp_path / "source.sqlite3")
    source_project = source_workspace.create_project("Incoming project")
    selected_files = tmp_path / "selected"
    selected_files.mkdir()
    package = export_workspace_project(
        source_workspace, source_project.project_id, selected_files,
        tmp_path / "incoming.thread",
    )

    destination_workspace = WorkspaceService(tmp_path / "destination.sqlite3")
    inspection = inspect_workspace_import(destination_workspace, package)

    assert inspection["has_conflicts"] is False
    assert inspection["candidate_projects"] == []
    assert inspection["record_collisions"] == []
    assert inspection["recommended_action"] == "import_as_new"
