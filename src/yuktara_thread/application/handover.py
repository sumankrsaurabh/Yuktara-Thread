"""Workspace-aware handover package compilation."""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.infrastructure.package import create_package


def export_workspace_project(
    workspace: WorkspaceService,
    project_id: str,
    files_directory: Path,
    output_file: Path,
) -> Path:
    """Compile project metadata, context, intelligence and selected files.

    The caller chooses the file directory explicitly. No files outside that
    directory are inspected or included.
    """
    project = workspace.projects.get(project_id)
    if project is None:
        raise LookupError("Project not found")
    if project.status != "active":
        raise ValueError("Archived projects must be restored before export")

    records = {
        kind: workspace.intelligence.list_records(project_id, kind)
        for kind in ("decision", "task", "milestone", "reference")
    }
    dependencies = [
        {"task_id": task["task_id"], "depends_on_task_id": dependency_id}
        for task in records["task"]
        for dependency_id in workspace.intelligence.list_task_dependencies(
            str(task["task_id"])
        )
    ]
    payload: dict[str, Any] = {
        **asdict(project),
        "context_sections": [
            asdict(section) for section in workspace.get_context(project_id)
        ],
        **{f"{kind}s": values for kind, values in records.items()},
        "task_dependencies": dependencies,
        "activity_events": workspace.intelligence.timeline(project_id, limit=1000),
        "handover_schema_version": 1,
    }
    return create_package(files_directory, output_file, payload)
