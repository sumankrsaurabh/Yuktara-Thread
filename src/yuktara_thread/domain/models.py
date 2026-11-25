"""Core data models for a portable project handover."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any
from uuid import uuid4


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(slots=True)
class ProjectContext:
    """Portable project context; intentionally independent of persistence/UI."""

    project_id: str
    name: str
    summary: str = ""
    goals: list[str] = field(default_factory=list)
    scope: list[str] = field(default_factory=list)
    current_state: str = ""
    unresolved_questions: list[str] = field(default_factory=list)
    constraints: list[str] = field(default_factory=list)
    handover_notes: str = ""
    created_at: str = field(default_factory=utc_now)
    updated_at: str = field(default_factory=utc_now)
    schema_version: int = 1

    @classmethod
    def create(cls, name: str, summary: str = "") -> "ProjectContext":
        clean_name = name.strip()
        if not clean_name:
            raise ValueError("Project name must not be empty")
        return cls(project_id=str(uuid4()), name=clean_name, summary=summary.strip())

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ProjectContext":
        allowed = {
            "project_id", "name", "summary", "goals", "scope", "current_state",
            "unresolved_questions", "constraints", "handover_notes", "created_at",
            "updated_at", "schema_version",
        }
        unknown = set(data) - allowed
        if unknown:
            raise ValueError(f"Unknown project fields: {', '.join(sorted(unknown))}")
        if not isinstance(data.get("project_id"), str) or not data["project_id"]:
            raise ValueError("project_id is required")
        if not isinstance(data.get("name"), str) or not data["name"].strip():
            raise ValueError("name is required")
        for key in ("goals", "scope", "unresolved_questions", "constraints"):
            value = data.get(key, [])
            if not isinstance(value, list) or not all(isinstance(x, str) for x in value):
                raise ValueError(f"{key} must be a list of strings")
        for key in ("summary", "current_state", "handover_notes", "created_at", "updated_at"):
            if key in data and not isinstance(data[key], str):
                raise ValueError(f"{key} must be a string")
        version = data.get("schema_version", 1)
        if not isinstance(version, int) or version != 1:
            raise ValueError("Unsupported project schema_version")
        return cls(**data)
