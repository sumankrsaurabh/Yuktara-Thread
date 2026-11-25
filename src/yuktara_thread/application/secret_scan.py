"""Local heuristic scan for likely secrets in explicitly selected handover files.

This is a warning system, not a guarantee that a file is free of secrets.
Matched values are never returned or logged.
"""
from __future__ import annotations

from pathlib import Path
import re

MAX_FILE_BYTES = 1_000_000
MAX_TOTAL_BYTES = 50_000_000
MAX_FILES = 10_000

_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("private-key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----")),
    ("github-token", re.compile(r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("slack-token", re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b")),
    ("generic-secret-assignment", re.compile(
        r"(?i)\b(?:api[_-]?key|access[_-]?token|client[_-]?secret|password|passwd|secret[_-]?key)\b"
        r"\s*[:=]\s*['\"]?[^\s'\"]{8,}"
    )),
)

_SENSITIVE_NAMES = {
    ".env", ".env.local", ".env.production", "credentials", "credentials.json",
    "id_rsa", "id_ed25519", "private.key",
}


def scan_selected_files(root: Path) -> dict:
    """Scan regular files beneath root; return paths/rules/line numbers, never values."""
    source = Path(root).resolve()
    if not source.is_dir():
        raise ValueError("Selected files path must be an existing directory")

    findings: list[dict] = []
    skipped: list[dict] = []
    scanned_files = 0
    scanned_bytes = 0
    for path in sorted(source.rglob("*")):
        if path.is_symlink() or not path.is_file():
            continue
        try:
            relative = path.relative_to(source).as_posix()
            size = path.stat().st_size
        except OSError:
            skipped.append({"path": str(path), "reason": "unreadable"})
            continue

        if scanned_files >= MAX_FILES:
            skipped.append({"path": relative, "reason": "file-count-limit"})
            break
        if size > MAX_FILE_BYTES:
            skipped.append({"path": relative, "reason": "file-size-limit"})
            continue
        if scanned_bytes + size > MAX_TOTAL_BYTES:
            skipped.append({"path": relative, "reason": "total-size-limit"})
            continue

        scanned_files += 1
        scanned_bytes += size
        if path.name.lower() in _SENSITIVE_NAMES or path.name.lower().startswith(".env."):
            findings.append({
                "path": relative, "line": 1, "rule": "sensitive-filename",
            })

        try:
            raw = path.read_bytes()
        except OSError:
            skipped.append({"path": relative, "reason": "unreadable"})
            continue
        if b"\x00" in raw:
            continue
        try:
            content = raw.decode("utf-8-sig")
        except UnicodeDecodeError:
            continue

        for line_number, line in enumerate(content.splitlines(), start=1):
            for rule, pattern in _PATTERNS:
                if pattern.search(line):
                    findings.append({
                        "path": relative, "line": line_number, "rule": rule,
                    })

    unique = {
        (item["path"], item["line"], item["rule"]): item for item in findings
    }
    ordered = sorted(unique.values(), key=lambda item: (item["path"], item["line"], item["rule"]))
    return {
        "findings": ordered,
        "finding_count": len(ordered),
        "scanned_files": scanned_files,
        "scanned_bytes": scanned_bytes,
        "skipped": skipped,
        "disclaimer": (
            "Heuristic scan only. False positives and undetected secrets are possible; "
            "review selected files before sharing."
        ),
    }
