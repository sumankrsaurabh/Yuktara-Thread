# Portable Handover Package Format

**Format ID:** `yuktara.thread`  
**Format version:** 1  
**Handover metadata schema:** 1

## Goals

- A package is portable and inspectable without a Yuktara account or network connection.
- Verification and preview never extract or execute package contents.
- Files are explicitly selected by the exporting user.
- The receiver can verify integrity before extraction or workspace import.
- Workspace import creates new local entity IDs and never overwrites an existing project or files directory.

## Archive layout

A package is a ZIP archive:

```text
project.thread
├── manifest.json
└── files/
    ├── README.md
    └── selected/path/to/file
```

The manifest contains:

- `format`: `yuktara.thread`
- `format_version`: integer format version
- `project`: project metadata and optional workspace handover records
- `files`: array of file records, each containing an archive path, uncompressed size and SHA-256 digest

The archive contains no directory entries. All file paths must be canonical relative POSIX paths below `files/`.

## Workspace handover metadata schema 1

Workspace-aware export stores these fields inside `project`:

- Project identity and display metadata (source IDs are informational only).
- `context_sections`: the six current context sections, including their current revision numbers.\n- `context_history`: up to 1,000 revision bodies per section, with original revision numbers and timestamps.
- `decisions`, `tasks`, `milestones`, `references`.
- `task_dependencies`: source task ID and prerequisite task ID pairs.
- `activity_events`: up to 1,000 recent event records.
- `handover_readiness`: deterministic completeness assessment calculated at export time. It is informational and does not certify correctness or safety.
- `handover_schema_version`: 1.
- `handover_readiness`: optional deterministic completeness result captured at export time; it is a documentation aid, not a safety or correctness certification.

The SQLite database itself is never packaged. Context revision bodies are included and restored. Workspace import replays validated source activity entries with imported-origin metadata while preserving source timestamps; these entries are unverified and do not prove who performed the original actions. Older packages without context_history remain importable.

The basic `thread create` command remains supported. It creates a package with project metadata and files but without workspace-specific records.

## Verification and resource limits

- Maximum archive entries: 2,000.
- Maximum uncompressed size per file: 50 MiB.
- Maximum total uncompressed payload: 250 MiB, plus the manifest limit.
- Maximum manifest size: 2 MiB.
- Duplicate, traversal, absolute, non-canonical and platform-unsafe paths are rejected.
- Symlinks, special files and directory entries are rejected.
- Every declared file must exist exactly once, match its declared size and pass SHA-256 verification.
- Undeclared archive entries are rejected.

SHA-256 detects accidental or malicious content changes relative to the manifest. It does **not** prove who created the package. Format v1 packages are not encrypted or digitally signed.

## Import behavior

1. Verify the archive and every file digest without extraction.
2. Validate workspace metadata, record fields and task dependency graph.
3. Extract files into a temporary sibling directory.
4. Recheck the manifest and each file while streaming extraction.
5. Publish the extracted directory only if the destination does not exist.
6. Restore project metadata, current context, structured records and task dependencies in one SQLite transaction.
7. Assign new local project and entity IDs; remap task prerequisite edges.\n8. Restore context revision snapshots and replay up to 1,000 validated source activity events as imported/unverified history.
9. If database restoration fails, remove the newly extracted directory.

Import does not execute files. The recipient should still independently inspect files before opening or running them. Import does not merge into an existing project; it creates a new project.

## Privacy and selection

The exporter receives one explicit source directory. Only regular files inside that directory are included. The SQLite database, other workspace projects and files outside the selected directory are not included. A local heuristic secret scan checks selected text files before export. Findings require explicit acknowledgement; this is not a guarantee that the package is free of secrets.
