from pathlib import Path

import pytest

from yuktara_thread.application.workspace import WorkspaceService


@pytest.fixture
def workspace(tmp_path: Path):
    service = WorkspaceService(tmp_path / "workspace.sqlite3")
    project = service.create_project("Thread test")
    return service, project


def test_schema_two_entities_and_events(workspace):
    service, project = workspace
    assert service.schema_version == 3
    decision = service.intelligence.create_decision(
        project.project_id, title="Use SQLite", rationale="Offline-first"
    )
    task = service.intelligence.create_task(
        project.project_id, title="Build importer", priority="high"
    )
    milestone = service.intelligence.create_milestone(project.project_id, title="MVP beta")
    reference = service.intelligence.create_reference(
        project.project_id, title="Repository", reference_type="repository"
    )
    assert decision["status"] == "proposed" and decision["alternatives"] == []
    assert task["priority"] == "high"
    assert milestone["status"] == "planned"
    assert reference["reference_type"] == "repository"
    events = service.intelligence.timeline(project.project_id)
    assert {"decision", "task", "milestone", "reference"} <= {
        event["entity_type"] for event in events
    }
    assert len(events) == 5  # includes project.created


def test_task_dependencies_reject_indirect_cycles(workspace):
    service, project = workspace
    repo = service.intelligence
    a = repo.create_task(project.project_id, title="A")
    b = repo.create_task(project.project_id, title="B")
    c = repo.create_task(project.project_id, title="C")
    repo.add_task_dependency(project.project_id, a["task_id"], b["task_id"])
    repo.add_task_dependency(project.project_id, b["task_id"], c["task_id"])
    with pytest.raises(ValueError, match="cycle"):
        repo.add_task_dependency(project.project_id, c["task_id"], a["task_id"])
    with pytest.raises(ValueError):
        repo.add_task_dependency(project.project_id, a["task_id"], a["task_id"])
    assert repo.list_task_dependencies(a["task_id"]) == [b["task_id"]]
    assert len(repo.timeline(project.project_id)) == 6  # project, tasks and dependency events


def test_invalid_status_and_foreign_project_dependency_rejected(workspace, tmp_path):
    service, project = workspace
    with pytest.raises(ValueError, match="decision status"):
        service.intelligence.create_decision(project.project_id, title="Invalid", status="unknown")
    other = WorkspaceService(tmp_path / "other.sqlite3")
    other_project = other.create_project("Other")
    foreign = other.intelligence.create_task(other_project.project_id, title="Foreign")
    local = service.intelligence.create_task(project.project_id, title="Local")
    with pytest.raises(ValueError, match="same project"):
        service.intelligence.add_task_dependency(project.project_id, local["task_id"], foreign["task_id"])


def test_timeline_limit_is_bounded(workspace):
    service, project = workspace
    with pytest.raises(ValueError):
        service.intelligence.timeline(project.project_id, limit=0)



def test_entity_update_and_delete_are_audited(workspace):
    service, project = workspace
    repo = service.intelligence
    decision = repo.create_decision(project.project_id, title="Initial choice")
    updated = repo.update_record(
        project.project_id, "decision", decision["decision_id"],
        title="Final choice", status="accepted", alternatives=["Option A", "Option B"]
    )
    assert updated["title"] == "Final choice"
    assert updated["status"] == "accepted"
    assert updated["alternatives"] == ["Option A", "Option B"]
    repo.delete_record(project.project_id, "decision", decision["decision_id"])
    assert repo.list_records(project.project_id, "decision") == []
    kinds = [event["event_type"] for event in repo.timeline(project.project_id)]
    assert {"decision.created", "decision.updated", "decision.deleted"} <= set(kinds)


def test_update_rejects_invalid_fields_and_missing_entities(workspace):
    service, project = workspace
    task = service.intelligence.create_task(project.project_id, title="Prepare release")
    with pytest.raises(ValueError, match="priority"):
        service.intelligence.update_record(
            project.project_id, "task", task["task_id"], priority="urgent"
        )
    with pytest.raises(ValueError, match="Unsupported"):
        service.intelligence.update_record(
            project.project_id, "task", task["task_id"], unexpected_field="other"
        )
    with pytest.raises(LookupError):
        service.intelligence.delete_record(project.project_id, "task", "missing")


def test_project_and_context_changes_appear_in_timeline(workspace):
    service, project = workspace
    service.update_project(project.project_id, "Renamed", "Updated summary")
    section = next(s for s in service.get_context(project.project_id) if s.section_key == "goals")
    service.save_context(project.project_id, "goals", "Ship v1", expected_revision=section.revision)
    events = service.intelligence.timeline(project.project_id)
    event_types = {event["event_type"] for event in events}
    assert {"project.created", "project.updated", "context.updated"} <= event_types
    context_event = next(event for event in events if event["event_type"] == "context.updated")
    assert context_event["payload"]["revision"] == 2


def test_task_dependency_removal_is_audited(workspace):
    service, project = workspace
    repo = service.intelligence
    task = repo.create_task(project.project_id, title="Parent")
    dependent = repo.create_task(project.project_id, title="Child")
    repo.add_task_dependency(project.project_id, dependent["task_id"], task["task_id"])
    repo.remove_task_dependency(project.project_id, dependent["task_id"], task["task_id"])
    assert repo.list_task_dependencies(dependent["task_id"]) == []
    assert "task.dependency_removed" in {
        event["event_type"] for event in repo.timeline(project.project_id)
    }



def test_entity_delete_is_recoverable_and_audited(workspace):
    service, project = workspace
    repo = service.intelligence
    task = repo.create_task(project.project_id, title="Recover this task")
    dependent = repo.create_task(project.project_id, title="Dependent task")
    repo.add_task_dependency(project.project_id, dependent["task_id"], task["task_id"])

    repo.delete_record(project.project_id, "task", task["task_id"])
    assert repo.list_records(project.project_id, "task") == [dependent]
    deleted = repo.list_records(project.project_id, "task", include_deleted=True)
    assert len(deleted) == 2
    assert next(item for item in deleted if item["task_id"] == task["task_id"])["deleted_at"]

    restored = service.restore_record(project.project_id, "task", task["task_id"])
    assert restored["task_id"] == task["task_id"]
    assert restored["title"] == "Recover this task"
    assert restored["deleted_at"] is None
    assert repo.list_task_dependencies(dependent["task_id"]) == [task["task_id"]]
    event_types = [event["event_type"] for event in repo.timeline(project.project_id)]
    assert "task.deleted" in event_types
    assert "task.restored" in event_types


def test_deleted_entities_cannot_be_restored_twice(workspace):
    service, project = workspace
    record = service.intelligence.create_reference(project.project_id, title="Docs")
    with pytest.raises(LookupError, match="Deleted reference not found"):
        service.restore_record(project.project_id, "reference", record["reference_id"])
    service.intelligence.delete_record(project.project_id, "reference", record["reference_id"])
    service.restore_record(project.project_id, "reference", record["reference_id"])
    with pytest.raises(LookupError, match="Deleted reference not found"):
        service.restore_record(project.project_id, "reference", record["reference_id"])



def test_soft_deleted_record_cannot_be_edited_until_restored(tmp_path):
    from yuktara_thread.application.workspace import WorkspaceService
    import pytest

    workspace = WorkspaceService(tmp_path / "deleted-edit.sqlite3")
    project = workspace.create_project("Deleted edit guard")
    task = workspace.intelligence.create_task(project.project_id, title="Do not edit")
    workspace.intelligence.delete_record(project.project_id, "task", task["task_id"])

    with pytest.raises(LookupError, match="not found in active project"):
        workspace.intelligence.update_record(
            project.project_id, "task", task["task_id"], title="Hidden edit"
        )

    restored = workspace.restore_record(project.project_id, "task", task["task_id"])
    assert restored["title"] == "Do not edit"



def test_deleted_record_purge_requires_confirmation_and_preserves_audit_event(tmp_path):
    from datetime import datetime, timedelta, timezone
    from yuktara_thread.application.workspace import WorkspaceService

    workspace = WorkspaceService(tmp_path / "purge.sqlite3")
    project = workspace.create_project("Retention policy")
    task = workspace.intelligence.create_task(project.project_id, title="Expired task")
    workspace.intelligence.delete_record(project.project_id, "task", task["task_id"])
    expired = (datetime.now(timezone.utc) - timedelta(days=90)).isoformat()
    with workspace.database.transaction() as connection:
        connection.execute(
            "UPDATE tasks SET deleted_at = ? WHERE task_id = ?",
            (expired, task["task_id"]),
        )

    preview = workspace.purge_deleted_records(
        project.project_id, "task", older_than_days=30
    )
    assert preview["purged"] is False
    assert preview["eligible_count"] == 1
    assert len(workspace.intelligence.list_records(
        project.project_id, "task", include_deleted=True
    )) == 1

    result = workspace.purge_deleted_records(
        project.project_id, "task", older_than_days=30, confirm=True
    )
    assert result["purged"] is True
    assert result["purged_count"] == 1
    assert workspace.intelligence.list_records(
        project.project_id, "task", include_deleted=True
    ) == []
    event_types = [
        event["event_type"] for event in workspace.intelligence.timeline(project.project_id)
    ]
    assert "task.deleted" in event_types
    assert "task.purged" in event_types


def test_deleted_record_purge_rejects_invalid_retention_days(tmp_path):
    from yuktara_thread.application.workspace import WorkspaceService
    import pytest

    workspace = WorkspaceService(tmp_path / "invalid-purge.sqlite3")
    project = workspace.create_project("Invalid retention")
    with pytest.raises(ValueError, match="between 1 and 36,500"):
        workspace.purge_deleted_records(project.project_id, "task", older_than_days=0)


def test_timeline_cursor_pages_are_complete_and_non_overlapping(workspace):
    service, project = workspace
    for index in range(7):
        service.intelligence.create_task(project.project_id, title=f"Task {index}")

    first_page = service.intelligence.timeline(project.project_id, limit=4)
    assert len(first_page) == 4
    oldest = first_page[-1]
    second_page = service.intelligence.timeline(
        project.project_id, limit=4,
        before=(oldest["created_at"], oldest["event_id"]),
    )
    assert len(second_page) == 4
    assert {event["event_id"] for event in first_page}.isdisjoint(
        event["event_id"] for event in second_page
    )
    combined = first_page + second_page
    assert combined == service.intelligence.timeline(project.project_id, limit=8)
    assert service.intelligence.timeline(
        project.project_id, limit=4,
        before=(second_page[-1]["created_at"], second_page[-1]["event_id"]),
    ) == []
