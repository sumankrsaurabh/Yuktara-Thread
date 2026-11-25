"""Repositories for decisions, tasks, milestones, references and project events."""
from __future__ import annotations
import json
from datetime import datetime, timezone
from uuid import uuid4

from yuktara_thread.infrastructure.database.connection import Database
from yuktara_thread.infrastructure.database.repositories.events import append_project_event


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


class ProjectIntelligenceRepository:
    """Transactional persistence for structured project knowledge and its activity stream."""
    TABLES = {
        "decision": ("decisions", "decision_id"),
        "task": ("tasks", "task_id"),
        "milestone": ("milestones", "milestone_id"),
        "reference": ("project_references", "reference_id"),
    }
    FIELDS = {
        "decision": {"title", "problem", "selected_option", "alternatives", "rationale", "consequences", "status"},
        "task": {"title", "description", "status", "priority", "owner", "due_at"},
        "milestone": {"title", "description", "due_at", "status"},
        "reference": {"title", "reference_type", "uri", "notes"},
    }

    def __init__(self, database: Database) -> None:
        self.database = database

    @staticmethod
    def _decode(kind: str, row: dict[str, object]) -> dict[str, object]:
        if kind == "decision":
            row["alternatives"] = json.loads(row.pop("alternatives_json"))
        return row

    def _validate(self, kind: str, values: dict[str, object]) -> dict[str, object]:
        if kind not in self.TABLES or not values or set(values) - self.FIELDS[kind]:
            raise ValueError("Unsupported or empty project record update")
        data = dict(values)
        if "title" in data:
            title = str(data["title"]).strip()
            if not title or len(title) > 240:
                raise ValueError("Title must contain 1–240 characters")
            data["title"] = title
        if kind == "decision":
            if data.get("status", "proposed") not in {"proposed", "accepted", "rejected", "superseded"}:
                raise ValueError("Invalid decision status")
            if "alternatives" in data:
                alternatives = data.pop("alternatives")
                if not isinstance(alternatives, list) or not all(isinstance(x, str) for x in alternatives):
                    raise ValueError("Decision alternatives must be a list of strings")
                data["alternatives_json"] = json.dumps(alternatives, ensure_ascii=False)
        elif kind == "task":
            if data.get("status", "open") not in {"open", "in_progress", "blocked", "completed", "cancelled"}:
                raise ValueError("Invalid task status")
            if data.get("priority", "normal") not in {"low", "normal", "high", "critical"}:
                raise ValueError("Invalid task priority")
        elif kind == "milestone":
            if data.get("status", "planned") not in {"planned", "in_progress", "completed", "cancelled"}:
                raise ValueError("Invalid milestone status")
        elif kind == "reference":
            if data.get("reference_type", "other") not in {"document", "repository", "website", "issue", "person", "other"}:
                raise ValueError("Invalid reference type")
        return data

    def validate_record_fields(self, kind: str, values: dict[str, object]) -> dict[str, object]:
        """Validate and normalize import-ready fields for one intelligence record."""
        return self._validate(kind, values)

    def _create(self, kind: str, project_id: str, values: dict[str, object]) -> dict[str, object]:
        table, id_column = self.TABLES[kind]
        defaults = {
            "decision": {"problem": "", "selected_option": "", "alternatives": [],
                         "rationale": "", "consequences": "", "status": "proposed"},
            "task": {"description": "", "status": "open", "priority": "normal", "owner": "", "due_at": None},
            "milestone": {"description": "", "due_at": None, "status": "planned"},
            "reference": {"reference_type": "other", "uri": "", "notes": ""},
        }[kind]
        data = self._validate(kind, {**defaults, **values})
        record_id, now = str(uuid4()), _now()
        columns = [id_column, "project_id", *data.keys(), "created_at", "updated_at"]
        params = [record_id, project_id, *data.values(), now, now]
        with self.database.transaction() as connection:
            project = connection.execute("SELECT status FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if project is None or project["status"] != "active":
                raise LookupError("Active project not found")
            connection.execute(
                f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join('?' for _ in columns)})",
                params,
            )
            append_project_event(connection, project_id=project_id, event_type=f"{kind}.created",
                entity_type=kind, entity_id=record_id, payload={"title": data["title"]}, created_at=now)
            row = connection.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", (record_id,)).fetchone()
        return self._decode(kind, dict(row))

    def create_decision(self, project_id: str, *, title: str, problem: str = "",
                        selected_option: str = "", alternatives: list[str] | None = None,
                        rationale: str = "", consequences: str = "", status: str = "proposed"):
        return self._create("decision", project_id, {"title": title, "problem": problem,
            "selected_option": selected_option, "alternatives": alternatives or [],
            "rationale": rationale, "consequences": consequences, "status": status})

    def create_task(self, project_id: str, *, title: str, description: str = "",
                    status: str = "open", priority: str = "normal", owner: str = "",
                    due_at: str | None = None):
        return self._create("task", project_id, {"title": title, "description": description,
            "status": status, "priority": priority, "owner": owner, "due_at": due_at})

    def create_milestone(self, project_id: str, *, title: str, description: str = "",
                         due_at: str | None = None, status: str = "planned"):
        return self._create("milestone", project_id, {"title": title, "description": description,
            "due_at": due_at, "status": status})

    def create_reference(self, project_id: str, *, title: str, reference_type: str = "other",
                         uri: str = "", notes: str = ""):
        return self._create("reference", project_id, {"title": title,
            "reference_type": reference_type, "uri": uri, "notes": notes})

    def update_record(self, project_id: str, entity_type: str, entity_id: str,
                      **changes: object) -> dict[str, object]:
        """Update an entity and append its event atomically."""
        if entity_type not in self.TABLES:
            raise ValueError("Unknown project entity type")
        table, id_column = self.TABLES[entity_type]
        data = self._validate(entity_type, changes)
        now = _now()
        assignments = ", ".join(f"{column} = ?" for column in data)
        with self.database.transaction() as connection:
            project = connection.execute("SELECT status FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if project is None or project["status"] != "active":
                raise LookupError("Active project not found")
            cursor = connection.execute(
                f"UPDATE {table} SET {assignments}, updated_at = ? WHERE {id_column} = ? AND project_id = ?",
                (*data.values(), now, entity_id, project_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"{entity_type.title()} not found in active project")
            append_project_event(connection, project_id=project_id, event_type=f"{entity_type}.updated",
                entity_type=entity_type, entity_id=entity_id,
                payload={"changed_fields": sorted(changes)}, created_at=now)
            row = connection.execute(f"SELECT * FROM {table} WHERE {id_column} = ?", (entity_id,)).fetchone()
        return self._decode(entity_type, dict(row))

    def delete_record(self, project_id: str, entity_type: str, entity_id: str) -> None:
        """Soft-delete an entity so it can be restored without losing its identity."""
        if entity_type not in self.TABLES:
            raise ValueError("Unknown project entity type")
        table, id_column = self.TABLES[entity_type]
        now = _now()
        with self.database.transaction() as connection:
            project = connection.execute("SELECT status FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if project is None or project["status"] != "active":
                raise LookupError("Active project not found")
            row = connection.execute(
                f"SELECT title FROM {table} WHERE {id_column} = ? AND project_id = ? AND deleted_at IS NULL",
                (entity_id, project_id),
            ).fetchone()
            if row is None:
                raise LookupError(f"Active {entity_type} not found")
            append_project_event(connection, project_id=project_id, event_type=f"{entity_type}.deleted",
                entity_type=entity_type, entity_id=entity_id, payload={"title": row["title"]}, created_at=now)
            connection.execute(
                f"UPDATE {table} SET deleted_at = ?, updated_at = ? WHERE {id_column} = ? AND project_id = ?",
                (now, now, entity_id, project_id),
            )

    def restore_record(self, project_id: str, entity_type: str, entity_id: str) -> dict[str, object]:
        """Restore a soft-deleted entity and append an audit event atomically."""
        if entity_type not in self.TABLES:
            raise ValueError("Unknown project entity type")
        table, id_column = self.TABLES[entity_type]
        now = _now()
        with self.database.transaction() as connection:
            project = connection.execute("SELECT status FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if project is None or project["status"] != "active":
                raise LookupError("Active project not found")
            cursor = connection.execute(
                f"UPDATE {table} SET deleted_at = NULL, updated_at = ? "
                f"WHERE {id_column} = ? AND project_id = ? AND deleted_at IS NOT NULL",
                (now, entity_id, project_id),
            )
            if cursor.rowcount != 1:
                raise LookupError(f"Deleted {entity_type} not found")
            append_project_event(connection, project_id=project_id, event_type=f"{entity_type}.restored",
                entity_type=entity_type, entity_id=entity_id, payload={}, created_at=now)
            row = connection.execute(
                f"SELECT * FROM {table} WHERE {id_column} = ? AND project_id = ?",
                (entity_id, project_id),
            ).fetchone()
        return self._decode(entity_type, dict(row))

    def list_records(self, project_id: str, entity_type: str, *,
                     include_deleted: bool = False) -> list[dict[str, object]]:
        if entity_type not in self.TABLES:
            raise ValueError("Unknown project entity type")
        table, _ = self.TABLES[entity_type]
        condition = "" if include_deleted else " AND deleted_at IS NULL"
        with self.database.read() as connection:
            rows = connection.execute(
                f"SELECT * FROM {table} WHERE project_id = ?{condition} ORDER BY created_at DESC",
                (project_id,),
            ).fetchall()
        return self._decode_rows(entity_type, rows)

    def _decode_rows(self, entity_type: str, rows) -> list[dict[str, object]]:
        return [self._decode(entity_type, dict(row)) for row in rows]

    def add_task_dependency(self, project_id: str, task_id: str, depends_on_task_id: str) -> None:
        now = _now()
        with self.database.transaction() as connection:
            rows = connection.execute(
                "SELECT task_id FROM tasks WHERE project_id = ? AND deleted_at IS NULL AND task_id IN (?, ?)",
                (project_id, task_id, depends_on_task_id),
            ).fetchall()
            if len(rows) != 2 or task_id == depends_on_task_id:
                raise ValueError("Both distinct tasks must belong to the same project")
            cycle = connection.execute(
                """WITH RECURSIVE reachable(task_id) AS (
                       SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ?
                       UNION SELECT d.depends_on_task_id FROM task_dependencies d
                       JOIN reachable r ON d.task_id = r.task_id
                   ) SELECT 1 FROM reachable WHERE task_id = ? LIMIT 1""",
                (depends_on_task_id, task_id),
            ).fetchone()
            if cycle:
                raise ValueError("Task dependency would create a cycle")
            connection.execute(
                "INSERT INTO task_dependencies(task_id, depends_on_task_id, created_at) VALUES (?, ?, ?)",
                (task_id, depends_on_task_id, now),
            )
            append_project_event(connection, project_id=project_id, event_type="task.dependency_added",
                entity_type="task", entity_id=task_id,
                payload={"depends_on_task_id": depends_on_task_id}, created_at=now)

    def remove_task_dependency(self, project_id: str, task_id: str,
                                depends_on_task_id: str) -> None:
        """Remove one prerequisite edge and append its event atomically."""
        now = _now()
        with self.database.transaction() as connection:
            project = connection.execute("SELECT status FROM projects WHERE project_id = ?", (project_id,)).fetchone()
            if project is None or project["status"] != "active":
                raise LookupError("Active project not found")
            cursor = connection.execute(
                """DELETE FROM task_dependencies
                   WHERE task_id = ? AND depends_on_task_id = ?
                   AND task_id IN (SELECT task_id FROM tasks WHERE project_id = ?)
                   AND depends_on_task_id IN (SELECT task_id FROM tasks WHERE project_id = ?)""",
                (task_id, depends_on_task_id, project_id, project_id),
            )
            if cursor.rowcount != 1:
                raise LookupError("Task dependency not found in project")
            append_project_event(connection, project_id=project_id,
                event_type="task.dependency_removed", entity_type="task", entity_id=task_id,
                payload={"depends_on_task_id": depends_on_task_id}, created_at=now)

    def list_task_dependencies(self, task_id: str) -> list[str]:
        with self.database.read() as connection:
            rows = connection.execute(
                "SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ? ORDER BY created_at",
                (task_id,),
            ).fetchall()
        return [row["depends_on_task_id"] for row in rows]

    def timeline(self, project_id: str, *, limit: int = 100) -> list[dict[str, object]]:
        if not 1 <= limit <= 1000:
            raise ValueError("Timeline limit must be between 1 and 1000")
        with self.database.read() as connection:
            rows = connection.execute(
                """SELECT event_id, event_type, entity_type, entity_id, payload_json, created_at
                   FROM project_events WHERE project_id = ?
                   ORDER BY created_at DESC, event_id DESC LIMIT ?""", (project_id, limit)
            ).fetchall()
        result = []
        for row in rows:
            item = dict(row)
            item["payload"] = json.loads(item.pop("payload_json"))
            result.append(item)
        return result
