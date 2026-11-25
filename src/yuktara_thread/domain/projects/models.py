"""Project entity and validation."""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

ProjectStatus = Literal["active", "archived"]

@dataclass(frozen=True, slots=True)
class Project:
    project_id: str
    name: str
    summary: str
    status: ProjectStatus
    created_at: str
    updated_at: str
    archived_at: str | None = None

    @classmethod
    def from_row(cls, row: object) -> "Project":
        return cls(
            project_id=row["project_id"], name=row["name"], summary=row["summary"],
            status=row["status"], created_at=row["created_at"],
            updated_at=row["updated_at"], archived_at=row["archived_at"],
        )

def validate_project_name(name: str) -> str:
    clean = name.strip()
    if not clean:
        raise ValueError("Project name must not be empty")
    if len(clean) > 160:
        raise ValueError("Project name must be 160 characters or fewer")
    return clean
