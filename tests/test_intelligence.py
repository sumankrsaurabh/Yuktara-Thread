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
    assert service.schema_version == 2
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
    assert {event["entity_type"] for event in events} == {
        "decision", "task", "milestone", "reference"
    }
    assert len(events) == 4


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
    assert len(repo.timeline(project.project_id)) == 5


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
