"""Workspace-aware handover package compilation."""
from __future__ import annotations

from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Any
from uuid import uuid4

from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.domain.context.models import CONTEXT_TITLES
from yuktara_thread.domain.projects.models import Project, validate_project_name
from yuktara_thread.infrastructure.database.repositories.events import append_project_event
from yuktara_thread.infrastructure.package import PackageError, create_package, import_package, preview_package


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


def import_workspace_project(
    workspace: WorkspaceService,
    package_file: Path,
    files_destination: Path,
) -> tuple[Project, Path]:
    """Restore a verified handover into a new workspace project.

    The package is verified before extraction. Database rows are inserted in
    one SQLite transaction. If that transaction fails, the newly extracted
    files directory is removed. Existing destinations are never overwritten.
    """
    preview = preview_package(package_file)
    source = preview["project"]
    name = source.get("name")
    summary = source.get("summary", "")
    if not isinstance(name, str):
        raise ValueError("Handover project name must be text")
    clean_name = validate_project_name(name)
    if not isinstance(summary, str):
        raise ValueError("Handover project summary must be text")

    schema_version = source.get("handover_schema_version")
    if schema_version is not None and (
        not isinstance(schema_version, int) or isinstance(schema_version, bool)
        or schema_version != 1
    ):
        raise ValueError("Unsupported handover schema version")

    sections_by_key: dict[str, str] = {}
    raw_sections = source.get("context_sections", [])
    if not isinstance(raw_sections, list) or len(raw_sections) > len(CONTEXT_TITLES):
        raise ValueError("Context sections must be a list of at most six items")
    for section in raw_sections:
        if not isinstance(section, dict):
            raise ValueError("Invalid context section")
        allowed_section_keys = {
            "section_id", "project_id", "section_key", "title", "content",
            "revision", "updated_at",
        }
        if set(section) - allowed_section_keys:
            raise ValueError("Context section contains unsupported fields")
        key, content = section.get("section_key"), section.get("content", "")
        if not isinstance(key, str) or key not in CONTEXT_TITLES or key in sections_by_key:
            raise ValueError(f"Unknown or duplicate context section: {key}")
        if not isinstance(content, str) or len(content) > 200_000:
            raise ValueError(f"Invalid context content for section: {key}")
        sections_by_key[key] = content

    kinds = ("decision", "task", "milestone", "reference")
    raw_records: dict[str, list[dict[str, Any]]] = {}
    for kind in kinds:
        records = source.get(f"{kind}s", [])
        if not isinstance(records, list) or len(records) > 500:
            raise ValueError(f"{kind.title()} records must be a list of at most 500 items")
        raw_records[kind] = []
        for record in records:
            if not isinstance(record, dict):
                raise ValueError(f"Invalid {kind} record")
            fields = workspace.intelligence.FIELDS[kind]
            table, id_column = workspace.intelligence.TABLES[kind]
            allowed_record_keys = fields | {
                id_column, "project_id", "created_at", "updated_at",
            }
            if set(record) - allowed_record_keys:
                raise ValueError(f"{kind.title()} record contains unsupported fields")
            values = {key: record[key] for key in fields if key in record}
            if not isinstance(values.get("title"), str) or not values["title"].strip():
                raise ValueError(f"Every {kind} must have a title")
            for key, value in values.items():
                if key == "alternatives":
                    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                        raise ValueError("Decision alternatives must be a list of strings")
                elif key == "due_at":
                    if value is not None and not isinstance(value, str):
                        raise ValueError(f"{kind} due_at must be text or null")
                elif not isinstance(value, str):
                    raise ValueError(f"{kind} field {key} must be text")
            validated = workspace.intelligence.validate_record_fields(kind, values)
            if kind == "task":
                validated["source_task_id"] = record.get("task_id")
            raw_records[kind].append(validated)

    raw_dependencies = source.get("task_dependencies", [])
    if not isinstance(raw_dependencies, list) or len(raw_dependencies) > 5000:
        raise ValueError("Task prerequisites must be a list of at most 5,000 items")
    source_task_ids = []
    for task in raw_records["task"]:
        source_id = task.get("source_task_id")
        if not isinstance(source_id, str) or not source_id or source_id in source_task_ids:
            raise ValueError("Every exported task must have a unique task ID")
        source_task_ids.append(source_id)

    task_id_map = {source_id: str(uuid4()) for source_id in source_task_ids}
    dependency_pairs: set[tuple[str, str]] = set()
    graph: dict[str, list[str]] = {task_id_map[source_id]: [] for source_id in source_task_ids}
    for dependency in raw_dependencies:
        if not isinstance(dependency, dict):
            raise ValueError("Invalid task prerequisite record")
        if set(dependency) - {"task_id", "depends_on_task_id", "created_at"}:
            raise ValueError("Task prerequisite contains unsupported fields")
        task_source = dependency.get("task_id")
        prerequisite_source = dependency.get("depends_on_task_id")
        if (
            not isinstance(task_source, str) or not isinstance(prerequisite_source, str)
            or task_source not in task_id_map or prerequisite_source not in task_id_map
        ):
            raise ValueError("Task prerequisite references a missing task")
        pair = (task_id_map[task_source], task_id_map[prerequisite_source])
        if pair[0] == pair[1] or pair in dependency_pairs:
            raise ValueError("Task prerequisite is self-referential or duplicated")
        dependency_pairs.add(pair)
        graph[pair[0]].append(pair[1])

    visiting: set[str] = set()
    visited: set[str] = set()

    def visit(task_id: str) -> None:
        if task_id in visiting:
            raise ValueError("Task prerequisites contain a dependency cycle")
        if task_id in visited:
            return
        visiting.add(task_id)
        for prerequisite_id in graph[task_id]:
            visit(prerequisite_id)
        visiting.remove(task_id)
        visited.add(task_id)

    for task_id in graph:
        visit(task_id)

    source_events = source.get("activity_events", [])
    if not isinstance(source_events, list) or len(source_events) > 1000:
        raise ValueError("Activity history must contain at most 1,000 events")

    extracted = import_package(package_file, files_destination)
    try:
        confirmed_preview = preview_package(package_file)
        if confirmed_preview["manifest_sha256"] != preview["manifest_sha256"]:
            raise PackageError("Package changed during workspace import")
    except Exception:
        shutil.rmtree(extracted, ignore_errors=True)
        raise
    project_id = str(uuid4())
    now = datetime.now(timezone.utc).isoformat()
    try:
        with workspace.database.transaction() as connection:
            connection.execute(
                """INSERT INTO projects
                   (project_id, name, summary, status, created_at, updated_at)
                   VALUES (?, ?, ?, 'active', ?, ?)""",
                (project_id, clean_name, summary.strip(), now, now),
            )
            append_project_event(
                connection, project_id=project_id, event_type="project.created",
                entity_type="project", entity_id=project_id,
                payload={"name": clean_name}, created_at=now,
            )
            for key, title in CONTEXT_TITLES.items():
                section_id = str(uuid4())
                content = sections_by_key.get(key, "")
                connection.execute(
                    """INSERT INTO context_sections
                       (section_id, project_id, section_key, title, content, revision, updated_at)
                       VALUES (?, ?, ?, ?, ?, 1, ?)""",
                    (section_id, project_id, key, title, content, now),
                )
                connection.execute(
                    """INSERT INTO context_revisions
                       (revision_id, section_id, revision, title, content, created_at)
                       VALUES (?, ?, 1, ?, ?, ?)""",
                    (str(uuid4()), section_id, title, content, now),
                )

            for kind in kinds:
                table, id_column = workspace.intelligence.TABLES[kind]
                for record in raw_records[kind]:
                    record_id = (
                        task_id_map[record["source_task_id"]]
                        if kind == "task" else str(uuid4())
                    )
                    data = dict(record)
                    data.pop("source_task_id", None)
                    columns = [id_column, "project_id", *data.keys(), "created_at", "updated_at"]
                    values = [record_id, project_id, *data.values(), now, now]
                    connection.execute(
                        f"INSERT INTO {table} ({', '.join(columns)}) "
                        f"VALUES ({', '.join('?' for _ in columns)})",
                        values,
                    )

            for task_id, prerequisite_id in dependency_pairs:
                connection.execute(
                    """INSERT INTO task_dependencies
                       (task_id, depends_on_task_id, created_at) VALUES (?, ?, ?)""",
                    (task_id, prerequisite_id, now),
                )

            append_project_event(
                connection, project_id=project_id, event_type="handover.imported",
                entity_type="handover", entity_id=None,
                payload={
                    "file_count": preview["file_count"],
                    "source_activity_event_count": len(source_events),
                    "context_section_count": len(sections_by_key),
                    "decision_count": len(raw_records["decision"]),
                    "task_count": len(raw_records["task"]),
                    "milestone_count": len(raw_records["milestone"]),
                    "reference_count": len(raw_records["reference"]),
                    "dependency_count": len(dependency_pairs),
                },
                created_at=now,
            )
        project = Project(
            project_id=project_id, name=clean_name, summary=summary.strip(),
            status="active", created_at=now, updated_at=now, archived_at=None,
        )
        return project, extracted
    except Exception:
        shutil.rmtree(extracted, ignore_errors=True)
        raise
