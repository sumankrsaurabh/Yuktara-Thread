"""Human-readable handover report rendering from a verified package preview."""
from __future__ import annotations

from typing import Any


def _text(value: Any) -> str:
    """Normalize untrusted metadata for a plain-text Markdown report."""
    return str(value).replace("\r\n", "\n").replace("\r", "\n").strip()


def render_handover_report(preview: dict[str, Any]) -> str:
    """Render a concise Markdown report; does not execute or extract package content."""
    project = preview["project"]
    name = _text(project.get("name") or "Unnamed project")
    summary = _text(project.get("summary") or "No summary provided")
    files = sorted(preview.get("files", []), key=lambda item: item["path"].casefold())
    total_bytes = sum(int(item["size"]) for item in files)

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
        "## Recipient checklist",
        "",
        "- Review the project summary and included files.",
        "- Confirm that no required files or context are missing.",
        "- Treat external links and files as untrusted until independently reviewed.",
        "- Record decisions, tasks and unresolved questions in the receiving workspace.",
        "",
    ])
    return "\n".join(lines)
