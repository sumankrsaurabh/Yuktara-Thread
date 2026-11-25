"""Context section types and supported keys."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Literal

ContextKey = Literal[
    "goals", "scope", "current_state", "unresolved_questions", "constraints", "handover_notes"
]
CONTEXT_TITLES: dict[str, str] = {
    "goals": "Goals",
    "scope": "Scope",
    "current_state": "Current state",
    "unresolved_questions": "Unresolved questions",
    "constraints": "Constraints",
    "handover_notes": "Handover notes",
}

@dataclass(frozen=True, slots=True)
class ContextSection:
    section_id: str
    project_id: str
    section_key: str
    title: str
    content: str
    revision: int
    updated_at: str
