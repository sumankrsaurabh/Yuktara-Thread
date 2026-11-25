# Yuktara Thread

**Keep the work. Keep the reasoning. Continue without losing context.**

Yuktara Thread is a local-first project continuity and handover platform. It preserves decisions, rationale, tasks, milestones, references and selected files so another person can understand and continue a project.

> **Development status:** pre-alpha; not production-ready. The repository now contains a Python core, SQLite workspace, optional PySide6 desktop application and portable `.thread` handover workflows. Cross-platform CI and release qualification are still in progress.

## Principles
- Local-first and usable offline.
- No account or cloud service required for core workflows.
- No automatic synchronization or silent data transfer.
- AI is optional and requires explicit approval before data transfer.
- Portable `.thread` packages with SHA-256 integrity checks.
- Non-destructive import inspection with project/context/count comparison and duplicate warnings; current imports always create a separate project.
- Importing a package must never execute its contents.

## Current foundation
- Python 3.11+; standard-library core.
- SQLite workspace with ordered transactional migrations, plus consistent local backup and validated restore into a new database file.
- Project create, read, list, update and archive operations.
- Structured context sections with revision history and stale-write protection.
- Decision, task, milestone and reference create/read/update/soft-delete/restore workflows, plus explicit dry-run-first retention purge.
- Append-only activity events for project, context, intelligence and task dependency changes; activity can be filtered by date/type/text and exported to JSON or Markdown.
- Task prerequisite relationships with cycle prevention and audited removal.
- Versioned ZIP-based `.thread` package creation, integrity verification, non-extracting preview and staged safe file extraction.
- Workspace-aware handover export/import for structured context and revision bodies, decisions, tasks, milestones, references, task prerequisites, up to 1,000 activity events and explicitly selected files. Import creates fresh local IDs, restores context history, replays source activity as clearly marked imported/unverified events and restores records in one transaction.
- Desktop package preview can import a verified handover into the open workspace.
- Markdown handover report export from a verified package preview, including decisions, tasks, dependencies and readiness assessment.
- Deterministic AI-free readiness checks on the project overview; checks distinguish required context from recommended detail.
- Local heuristic secret scan before handover export; flagged exports require explicit user acknowledgement, and matched values are never displayed.
- Safe extraction rejects existing destinations, validates manifest metadata and file hashes, and removes staging data on failure.
- CLI commands for package creation/verification and local workspace/project management.
- Optional PySide6 desktop application (`.[desktop]`) with first-run workspace selection, project editing/archive, context editing and revision history, structured intelligence forms, task prerequisites and dependency map, deleted-record recovery, searchable/filterable/exportable activity, verified package preview, workspace import, file extraction and Markdown handover report export.
- Automated tests and GitHub Actions CI for Python 3.11–3.13, with Windows/macOS/Linux platform smoke and portable-bundle builds included in CI. The desktop shell includes initial accessible control labels and keyboard shortcuts: Ctrl+N (new project), Ctrl+K (search), Ctrl+O (preview package).

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
- [Software architecture](docs/architecture/SOFTWARE_ARCHITECTURE.md): layer boundaries, transaction rules, source organization and engineering workflow.
- [Contributing](CONTRIBUTING.md): development setup, engineering rules, tests and pull-request checklist.
- [Portable package format v1](docs/architecture/PACKAGE_FORMAT.md): archive layout, metadata schema, limits and import behavior.
- [Portable desktop builds](docs/release/PORTABLE_BUILDS.md): build artifacts, launch instructions and signing limitations.
- [Release qualification checklist](docs/release/RELEASE_QUALIFICATION.md): required automated, manual, security and distribution gates.
- [Changelog](CHANGELOG.md): implementation milestones and known limitations.
- `src/yuktara_thread/cli`: command-line interface.
- `src/yuktara_thread/ui`: optional PySide6 presentation layer, split into context editors, project panels, dialogs, page composition and the main-window orchestrator.
- `tests`: automated tests.
- `docs`: product, architecture, security and development documentation.

## Roadmap
See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md) and [roadmap](docs/product/ROADMAP.md). Remaining release work: platform QA, installers, accessibility review, security hardening and release qualification.

## Security
Package verification checks integrity, not publisher identity. Packages are not encrypted or signed. This project has not undergone an independent security audit. See [SECURITY.md](SECURITY.md) and [threat model](docs/security/THREAT_MODEL.md).

## License
All rights reserved pending a deliberate licensing decision. See [LICENSE](LICENSE).
