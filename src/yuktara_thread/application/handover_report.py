"""Human-readable handover report rendering from a verified package preview."""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    """Normalize untrusted metadata for a plain-text Markdown report."""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def _list(value: Any) -> list:
    """Treat malformed optional collections as absent in a preview report."""
    return value if isinstance(value, list) else []


def render_handover_report(preview: dict[str, Any]) -> str:
    """Render a concise Markdown report; does not execute or extract package content."""
    project = preview["project"]
    name = _text(project.get("name") or "Unnamed project")
    summary = _text(project.get("summary") or "No summary provided")
    files = sorted(preview.get("files", []), key=lambda item: item["path"].casefold())
    total_bytes = sum(int(item["size"]) for item in files)

    context_sections = _list(project.get("context_sections", []))
    decisions = _list(project.get("decisions", []))
    tasks = _list(project.get("tasks", []))
    milestones = _list(project.get("milestones", []))
    references = _list(project.get("references", []))
    dependencies = _list(project.get("task_dependencies", []))
    events = _list(project.get("activity_events", []))
    lines = [
        f"# Handover: {name}",
        "",
        summary,
        "",
        "## Package details",
        "",
        f"- Format: {preview['format']} v{preview['format_version']}",
        f"- Files: {len(files)}",
        f"- Total uncompressed size: {total_bytes:,} bytes",
        f"- Context sections: {len(context_sections)}",
        f"- Decisions: {len(decisions)}",
        f"- Tasks: {len(tasks)}",
        f"- Milestones: {len(milestones)}",
        f"- References: {len(references)}",
        f"- Task prerequisites: {len(dependencies)}",
        f"- Activity events included: {len(events)}",
        "- Integrity: SHA-256 verification passed",
        "- Authenticity: not established by integrity verification",
        "",
        "## Included files",
        "",
    ]
    if files:
        lines.extend(f"- `{item['path']}` — {int(item['size']):,} bytes" for item in files)
    else:
        lines.append("- No files included.")
    lines.extend([
        "",
        "## Project context",
        "",
    ])
    if context_sections:
        for section in context_sections:
            title = _text(section.get("title") or section.get("section_key") or "Context")
            content = _text(section.get("content") or "")
            lines.extend([f"### {title}", "", content or "_No content recorded._", ""])
    else:
        lines.extend(["No structured context sections were included.", ""])
    lines.extend(["## Decisions", ""])
    if decisions:
        for decision in decisions:
            lines.extend([
                f"### {_text(decision.get('title') or 'Untitled decision')}",
                "",
                f"- Status: {_text(decision.get('status') or 'proposed')}",
                f"- Problem: {_text(decision.get('problem') or 'Not recorded')}",
                f"- Selected option: {_text(decision.get('selected_option') or 'Not recorded')}",
                f"- Rationale: {_text(decision.get('rationale') or 'Not recorded')}",
                f"- Alternatives: {', '.join(_text(item) for item in decision.get('alternatives', [])) or 'Not recorded'}",
                f"- Consequences: {_text(decision.get('consequences') or 'Not recorded')}",
                "",
            ])
    else:
        lines.extend(["No decisions included.", ""])

    lines.extend(["## Tasks", ""])
    if tasks:
        for task in tasks:
            lines.extend([
                f"### {_text(task.get('title') or 'Untitled task')}",
                "",
                f"- Status: {_text(task.get('status') or 'open')}",
                f"- Priority: {_text(task.get('priority') or 'normal')}",
                f"- Owner: {_text(task.get('owner') or 'Unassigned')}",
                f"- Due: {_text(task.get('due_at') or 'Not scheduled')}",
                _text(task.get("description") or "No description recorded."),
                "",
            ])
    else:
        lines.extend(["No tasks included.", ""])

    lines.extend(["## Milestones", ""])
    if milestones:
        for milestone in milestones:
            lines.extend([
                f"- **{_text(milestone.get('title') or 'Untitled milestone')}** — "
                f"{_text(milestone.get('status') or 'planned')}; "
                f"due {_text(milestone.get('due_at') or 'not scheduled')}",
            ])
    else:
        lines.append("No milestones included.")
    lines.extend(["", "## References", ""])
    if references:
        for reference in references:
            lines.append(
                f"- **{_text(reference.get('title') or 'Untitled reference')}** "
                f"({_text(reference.get('reference_type') or 'other')}): "
                f"{_text(reference.get('uri') or 'No URI')} — "
                f"{_text(reference.get('notes') or 'No notes')}"
            )
    else:
        lines.append("No references included.")
    lines.extend(["", "## Task prerequisites", ""])
    task_titles = {item.get("task_id"): _text(item.get("title") or "Untitled task") for item in tasks}
    if dependencies:
        for dependency in dependencies:
            task_title = task_titles.get(dependency.get("task_id"), "Unknown task")
            prerequisite_title = task_titles.get(
                dependency.get("depends_on_task_id"), "Unknown prerequisite"
            )
            lines.append(f"- {task_title} depends on {prerequisite_title}")
    else:
        lines.append("No task prerequisites recorded.")
    lines.extend([
        "",
        "## Recipient checklist",
        "",
        "- Review the project summary and included files.",
        "- Confirm that no required files or context are missing.",
        "- Treat external links and files as untrusted until independently reviewed.",
        "- Record decisions, tasks and unresolved questions in the receiving workspace.",
        "",
    ])
    return "\n".join(lines)
