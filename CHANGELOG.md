# Changelog

All notable changes to Yuktara Thread are documented here. Development versions may change before a stable release.

## 0.6.6.dev0 — 2026-11-25

### Added
- Durable SQLite import journal records package manifest hash, destination, project ID, phase, state and timestamps before file extraction.
- Project creation and the `database_committed` journal transition commit atomically in one SQLite transaction.
- Non-destructive reconciliation finalizes committed imports and flags orphaned files or missing files for manual recovery; attempts updated in the previous five minutes are skipped to avoid racing a live import.
- `thread import-recovery --database PATH` reports and reconciles interrupted workspace imports.
- Regression coverage for completed imports, failed imports, retained orphan files, committed import finalization and CLI reconciliation.

### Limitations
- Recovery reconciliation is explicit, not automatic at application startup. Ambiguous states are never deleted or overwritten.

## 0.6.5.dev0 — 2026-11-25

### Added
- Failed workspace imports report the failing phase and verify whether extracted files were removed.
- When automatic cleanup fails, the error identifies the retained directory and instructs the operator to confirm that no project was created before manual recovery.
- Regression coverage for failed database imports whose extracted files cannot be cleaned up.

## 0.6.4.dev0 — 2026-11-25

### Added
- Structured source-versus-destination project comparison during import inspection, including project summary, context section differences/revisions and decision/task/milestone/reference record counts.
- Desktop import warning now presents detected project, context and record-count differences before explicit confirmation.
- Regression coverage for differing local context content and non-destructive comparison.

### Fixed
- Corrected malformed literal line breaks in the package preview and workspace search dialogs that caused Python compilation to fail across platforms.

### Limitations
- Comparison is read-only and advisory. It does not merge, replace or automatically reconcile records.


## 0.6.3.dev0 — 2026-11-25

### Added
- Non-destructive workspace import inspection before extraction or database writes.
- Candidate detection by source project ID and case-insensitive project name, plus advisory title collisions for decisions, tasks, milestones and references.
- Desktop warning and explicit confirmation when an incoming handover resembles existing workspace content; import continues to create a separate project and never merges or replaces records.
- Regression tests proving conflict inspection leaves the destination workspace unchanged.

### Limitations
- Conflict detection is advisory and based on project identity/name and exact normalized record titles; it does not perform semantic matching or merge records.


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
