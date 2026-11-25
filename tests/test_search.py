from pathlib import Path

import pytest

from yuktara_thread.application.search import search_workspace
from yuktara_thread.application.workspace import WorkspaceService


def test_search_finds_projects_context_and_structured_records(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "search.sqlite3")
    project = workspace.create_project("Nova UI", "Custom desktop rendering toolkit")
    workspace.save_context(
        project.project_id, "goals", "Support offline-first application development",
        expected_revision=1,
    )
    workspace.intelligence.create_decision(
        project.project_id, title="Rendering backend",
        problem="Need GPU acceleration", rationale="Keep drawing responsive",
    )
    workspace.intelligence.create_task(
        project.project_id, title="Implement shader cache",
        description="Add a local shader cache",
    )
    workspace.intelligence.create_milestone(
        project.project_id, title="Offline release",
        description="Package without network dependencies",
    )
    workspace.intelligence.create_reference(
        project.project_id, title="Graphics notes",
        uri="docs/gpu-rendering.md", notes="Shader cache design",
    )

    assert any(item["entity_type"] == "project"
               for item in search_workspace(workspace, "rendering"))
    assert any(item["entity_type"] == "context"
               for item in search_workspace(workspace, "offline-first"))
    assert any(item["entity_type"] == "decision"
               for item in search_workspace(workspace, "acceleration"))
    assert any(item["entity_type"] == "task"
               for item in search_workspace(workspace, "shader cache"))
    assert any(item["entity_type"] == "milestone"
               for item in search_workspace(workspace, "network dependencies"))
    assert any(item["entity_type"] == "reference"
               for item in search_workspace(workspace, "gpu-rendering"))


def test_search_excludes_archived_projects_by_default(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "search-archive.sqlite3")
    project = workspace.create_project("Archived research", "Unique archived topic")
    workspace.archive_project(project.project_id)

    assert search_workspace(workspace, "archived topic") == []
    results = search_workspace(workspace, "archived topic", include_archived=True)
    assert len(results) == 1
    assert results[0]["project_id"] == project.project_id


@pytest.mark.parametrize(
    ("query", "limit", "message"),
    [
        ("x", 10, "at least 2 characters"),
        ("valid query", 0, "between 1 and 100"),
        ("valid query", 101, "between 1 and 100"),
    ],
)
def test_search_validates_query_and_limit(
    tmp_path: Path, query: str, limit: int, message: str
) -> None:
    workspace = WorkspaceService(tmp_path / "search-validation.sqlite3")
    with pytest.raises(ValueError, match=message):
        search_workspace(workspace, query, limit=limit)


def test_search_treats_sql_wildcards_as_literal_text(tmp_path: Path) -> None:
    workspace = WorkspaceService(tmp_path / "search-literal.sqlite3")
    workspace.create_project("100% complete", "Literal percent in title")

    assert len(search_workspace(workspace, "100%")) == 1
    assert search_workspace(workspace, "100_") == []
