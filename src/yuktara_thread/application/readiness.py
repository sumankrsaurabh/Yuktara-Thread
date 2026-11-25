"""Deterministic, AI-free handover completeness checks."""
from __future__ import annotations

from typing import Any


def _value(record: Any, key: str, default: Any = None) -> Any:
    if isinstance(record, dict):
        return record.get(key, default)
    return getattr(record, key, default)


def assess_handover_readiness(
    project: Any,
    context_sections: list[Any],
    decisions: list[dict[str, Any]],
    tasks: list[dict[str, Any]],
    milestones: list[dict[str, Any]],
    references: list[dict[str, Any]],
    *,
    selected_file_count: int | None = None,
) -> dict[str, Any]:
    """Return a transparent completeness indicator, not a quality guarantee."""
    sections = {
        str(_value(section, "section_key", "")): str(_value(section, "content", "") or "").strip()
        for section in context_sections
    }
    checks: list[dict[str, Any]] = []

    def add(key: str, label: str, passed: bool, required: bool, detail: str) -> None:
        checks.append({
            "key": key, "label": label, "passed": bool(passed),
            "required": required, "detail": detail,
        })

    add(
        "project_summary", "Project summary",
        bool(str(_value(project, "summary", "") or "").strip()), True,
        "A concise summary explains the project's purpose.",
    )
    for key, label in (
        ("goals", "Goals"),
        ("current_state", "Current state"),
        ("handover_notes", "Handover notes"),
    ):
        add(
            key, label, bool(sections.get(key)), True,
            f"Record the {label.lower()} another person needs to continue.",
        )

    for key, label in (("scope", "Scope"), ("unresolved_questions", "Unresolved questions")):
        add(
            key, label, bool(sections.get(key)), False,
            f"Clarify {label.lower()}, or explicitly record 'None'.",
        )

    add(
        "tasks_recorded", "Tasks",
        bool(tasks), False,
        "Record remaining work, or explicitly state that no tasks remain.",
    )
    open_tasks = [
        task for task in tasks
        if str(task.get("status") or "open") not in {"completed", "cancelled"}
    ]
    tasks_without_details = [
        task for task in open_tasks if not str(task.get("description") or "").strip()
    ]
    if open_tasks:
        add(
            "open_task_details", "Open task descriptions",
            not tasks_without_details, False,
            "Add a short description to every open task.",
        )

    decisions_without_rationale = [
        decision for decision in decisions
        if not str(decision.get("rationale") or "").strip()
    ]
    if decisions:
        add(
            "decision_rationale", "Decision rationale",
            not decisions_without_rationale, False,
            "Explain why each recorded decision was made.",
        )

    add(
        "references", "References",
        bool(references), False,
        "Add links or locations for important project resources.",
    )
    if selected_file_count is not None:
        add(
            "selected_files", "Selected files",
            selected_file_count > 0, False,
            "Include the files the recipient needs, or document why no files are required.",
        )

    weight_total = sum(2 if check["required"] else 1 for check in checks)
    weight_passed = sum(
        (2 if check["required"] else 1) for check in checks if check["passed"]
    )
    score = round(100 * weight_passed / weight_total) if weight_total else 100
    missing_required = [check for check in checks if check["required"] and not check["passed"]]
    missing_recommended = [check for check in checks if not check["required"] and not check["passed"]]
    status = (
        "incomplete" if missing_required
        else "needs_attention" if missing_recommended
        else "ready_for_review"
    )
    return {
        "score": score,
        "status": status,
        "required_complete": not missing_required,
        "checks": checks,
        "missing_required": [check["key"] for check in missing_required],
        "missing_recommended": [check["key"] for check in missing_recommended],
        "disclaimer": "Completeness indicator only; it does not verify correctness, safety or authenticity.",
    }
