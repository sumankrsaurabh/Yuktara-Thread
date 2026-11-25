# Yuktara Thread

**Keep the work. Keep the reasoning. Continue without losing context.**

Yuktara Thread is a local-first project continuity and handover platform. It preserves decisions, rationale, tasks, milestones, references and selected files so another person can understand and continue a project.

> **Development status:** early pre-alpha. Not production-ready. This repository contains a Python core, SQLite workspace and project intelligence foundation, and prototype portable handover package format. An initial optional PySide6 desktop shell is now available for workspace projects, context, intelligence records and activity history.

## Principles
- Local-first and usable offline.
- No account or cloud service required for core workflows.
- No automatic synchronization or silent data transfer.
- AI is optional and requires explicit approval before data transfer.
- Portable `.thread` packages with SHA-256 integrity checks.
- Importing a package must never execute its contents.

## Current foundation
- Python 3.11+; standard-library core.
- SQLite workspace with ordered transactional migrations.
- Project create, read, list, update and archive operations.
- Structured context sections with revision history and stale-write protection.
- Decision, task, milestone and reference create/read/update/delete workflows.
- Append-only activity events for project, context, intelligence and task dependency changes.
- Task prerequisite relationships with cycle prevention and audited removal.
- Versioned ZIP-based `.thread` package creation, integrity verification, non-extracting preview and staged safe file extraction.
- Workspace-aware handover export/import for structured context, decisions, tasks, milestones, references, task prerequisites, recent activity counts and explicitly selected files. Import creates fresh local IDs and restores database records in one transaction.
- Desktop package preview can import a verified handover into the open workspace.
- Markdown handover report export from a verified package preview.
- Safe extraction rejects existing destinations, validates manifest metadata and file hashes, and removes staging data on failure.
- CLI commands for package creation/verification and local workspace/project management.
- Optional PySide6 6.9 desktop shell (`.[desktop]`) with project editing/archive, context editing, structured intelligence forms, task prerequisites, searchable activity, verified package preview, workspace import, file extraction and Markdown handover report export.
- Automated tests and GitHub Actions CI matrix.

## Quick start
```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -e ".[dev,desktop]"
thread create --input examples/sample-project --output sample.thread
thread verify sample.thread
pytest
thread desktop --database ./workspace.sqlite3
```

## Workspace API
```python
from pathlib import Path
from yuktara_thread.application.workspace import WorkspaceService

workspace = WorkspaceService(Path.home() / ".yuktara-thread" / "workspace.sqlite3")
project = workspace.create_project("Website redesign", "Customer portal refresh")
sections = workspace.get_context(project.project_id)
goals = next(section for section in sections if section.section_key == "goals")
workspace.save_context(project.project_id, "goals", "Deliver accessible responsive UI",
                       expected_revision=goals.revision)
```

## Workspace CLI

Initialize a database with `thread workspace init --database ./workspace.sqlite3`, then create/list/archive projects with `thread project`. See [CLI guide](docs/development/CLI.md).

## Repository map
- `src/yuktara_thread/domain`: framework-independent domain models.
- `src/yuktara_thread/application`: use-case orchestration.
- `src/yuktara_thread/infrastructure/database`: SQLite connection, migrations and repositories.
- `src/yuktara_thread/infrastructure/package.py`: package serialization and verification.
- [Portable package format v1](docs/architecture/PACKAGE_FORMAT.md): archive layout, metadata schema, limits and import behavior.
- `src/yuktara_thread/cli`: command-line interface.
- `src/yuktara_thread/ui`: optional PySide6 presentation layer.
- `tests`: automated tests.
- `docs`: product, architecture, security and development documentation.

## Roadmap
See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [roadmap](docs/product/ROADMAP.md). Next: readiness checks, secret-inclusion review, full source activity-history replay and cross-platform packaging.

## Security
Package verification checks integrity, not publisher identity. Packages are not encrypted or signed. This project has not undergone an independent security audit. See [SECURITY.md](SECURITY.md) and [threat model](docs/security/THREAT_MODEL.md).

## License
All rights reserved pending a deliberate licensing decision. See [LICENSE](LICENSE).
