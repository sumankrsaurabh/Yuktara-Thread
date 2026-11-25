# Changelog

All notable changes to Yuktara Thread are documented here. Development versions may change before a stable release.

## 0.6.2.dev0 — 2026-11-25

### Added
- Stable cursor-based pagination for project activity using `(created_at, event_id)` ordering.
- Desktop activity timeline loads 100 events at a time with an explicit Load older activity action.
- Timeline pagination regression coverage for complete, non-overlapping pages and desktop incremental loading.


## 0.6.1.dev0 — 2026-11-25

### Added
- Accessible names and descriptions for key workspace, project, context, intelligence and activity controls.
- Predictable keyboard tab order through the main workspace sidebar.
- Window-level shortcuts: Ctrl+N to create a project, Ctrl+K to search, and Ctrl+O to preview a .thread package.
- Offscreen UI regression coverage for accessible names, focusability and shortcut registration.

### Limitations
- This is an initial accessibility foundation, not a completed accessibility audit. Screen-reader, contrast, focus-indicator and real-platform assistive-technology testing remain required.


## 0.6.0.dev0 — 2026-11-25

### Added
- Context revision history inspection and restore-as-new-revision in the desktop application.
- Context revision-body preservation across .thread handover export and import.
- Validated source activity-history replay, with imported/unverified provenance metadata.
- Desktop recovery dialog for soft-deleted decisions, tasks, milestones and references.
- Explicit age-based retention purge with dry-run by default, confirmation required and a permanent audit event.
- Activity text, event-type and inclusive date-range filtering; JSON and Markdown export.
- Activity refresh control to load events created after the panel was opened.
- Read-only layered task dependency map.
- First-run workspace selection for desktop launches without an explicit database argument.
- Portable PyInstaller bundle workflows for Windows, macOS and Linux, with SHA-256 checksum artifacts.
- Cross-platform desktop smoke-test matrix and wheel/source-distribution validation.
- Modular desktop source layout and software architecture/release qualification documentation.

### Fixed
- Handover import accepts nullable soft-delete metadata without importing deleted records.
- Soft-deleted records cannot be edited until restored.
- Task dependency creation requires an active project and active task records.
- Retention purge avoids SQLite bind-parameter limits for large eligible sets.
- Handover export bounds context history and import validates revision continuity and activity metadata.

### Limitations
- Pre-alpha; not production-ready.
- Portable bundles are unsigned. Signed installers and interactive manual QA are not complete.
- Packages and workspace backups are not encrypted or publisher-authenticated.
- Secret scanning is heuristic and not a DLP or malware scanner.
- Optional local/cloud AI adapters, import merge workflows and independent security review remain pending.

## 0.5.0.dev0 — Privacy, recovery and search foundation

- Add local heuristic secret review before CLI and desktop handover export, with explicit acknowledgement when findings exist.
- Add SQLite online workspace backup and validated restore into a new database path, available in the CLI and desktop shell.
- Add bounded workspace-wide search for project summaries, context sections, decisions, tasks, milestones and references, with CLI and desktop entry points.
- Validate backup integrity, foreign-key consistency, required workspace tables and migration history before publishing restored data.

## 0.4.0.dev0 — Workspace-aware handover and privacy review

- Export complete workspace context, decisions, tasks, milestones, references, task prerequisites and recent activity metadata into .thread packages.
- Restore verified handovers into a new local workspace with fresh IDs and dependency remapping.
- Add desktop package preview, workspace import and Markdown handover report export.
- Add deterministic AI-free readiness checks in the project overview and handover report.
- Add local heuristic secret scanning before CLI and desktop handover export, with explicit acknowledgement when possible credentials are detected.
- Harden package creation with strict JSON metadata, isolated temporary files and post-write verification.
- Add import validation and transactional database restoration.

This remains a pre-alpha development version. It is not a production release.

## 0.1.0 — Initial foundation

- Establish Python package and repository conventions.
- Add portable ZIP package creation and integrity verification.
- Add CLI entry points and package tests.
- Add product, architecture, security and implementation-status documents.

This is a pre-alpha engineering foundation, not a production release.
