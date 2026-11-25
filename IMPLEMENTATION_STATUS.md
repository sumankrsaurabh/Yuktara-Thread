# Implementation Status

**Release:** 0.6.3.dev0  
**Status:** pre-alpha; not production-ready

## Implemented
- [x] Python package skeleton and CLI.
- [x] Versioned ZIP package writer and SHA-256 integrity verifier.
- [x] Verified package preview and staged safe file extraction with no-overwrite destination handling.
- [x] Archive path hardening for traversal, non-canonical paths, Windows-reserved names and non-regular entries.
- [x] SQLite workspace with ordered transactional migrations (schema v1–v3).
- [x] Project create/get/list/update/archive with transactional activity events.
- [x] Six structured context sections with append-only revision snapshots, optimistic concurrency, desktop history inspection and restore-as-new-revision.
- [x] Context revision events in the project timeline.
- [x] Decision, task, milestone and reference create/list/update operations.
- [x] Recoverable soft-delete and restore for decisions, tasks, milestones and references, with audited lifecycle events.
- [x] Explicit age-based purge with dry-run by default, confirmation required for permanent deletion, and retained purge audit event.
- [x] Desktop deleted-record review and restore dialog; edits to deleted records are rejected until restoration.
- [x] Append-only project event records for project, context, intelligence entity and dependency mutations.
- [x] Task prerequisite relationships with cross-project, self-link and cycle rejection, plus audited edge removal.
- [x] Bounded project activity timeline query with stable cursor-based pagination.
- [x] Modular PySide6 desktop application with first-run workspace selection, project navigation, context editors, intelligence panels, dialogs and activity timeline.
- [x] Initial accessibility improvements: descriptive accessible names, accessible descriptions for key controls, predictable sidebar tab order, and Ctrl+N / Ctrl+K / Ctrl+O shortcuts.
- [x] Project metadata editing and audited project archiving from the desktop UI.
- [x] Archived-project inspection and audited restoration from the desktop UI and CLI.
- [x] Task prerequisite add/remove controls using cycle-safe application services.
- [x] Human-readable activity labels with text search, event-type and inclusive date-range filtering, explicit refresh and incremental 100-event pagination.
- [x] Activity export to JSON and Markdown for the currently filtered event set.
- [x] Structured desktop forms for decision, task, milestone and reference fields.
- [x] Offscreen Qt smoke tests covering window startup, structured forms, task prerequisites, project archiving and activity filtering.
- [x] Desktop package preview dialog with explicit file extraction to a user-selected new folder.
- [x] Non-destructive handover import inspection: candidate project detection by source ID/name and exact normalized title collisions across decisions, tasks, milestones and references.
- [x] Desktop warning and explicit confirmation before importing a handover that resembles existing workspace content; import remains import-as-new only.
- [x] Desktop import of verified handovers into the active workspace.
- [x] Markdown handover report generated from verified package metadata, file inventory, structured project context and readiness assessment.
- [x] Deterministic AI-free handover readiness checks in project overview and exported reports.
- [x] Local bounded secret-pattern scan before CLI and desktop export; findings do not reveal matched values and require explicit acknowledgement.
- [x] SQLite online backup and validated restore to a new database path, with no-overwrite publication in CLI and desktop.
- [x] Bounded local search across project summaries, context, decisions, tasks, milestones and references, with archived-project filtering.
- [x] Workspace-aware package export for context sections and their revision bodies, decisions, tasks, milestones, references, task dependencies and recent activity.
- [x] CLI command for workspace-aware project export with an explicit selected-files directory.
- [x] Recipient-side workspace import with new local IDs, full context revision history restoration, current records, task dependency remapping and marked source activity-history replay.
- [x] Atomic SQLite restoration transaction; failed database restoration removes newly extracted files.
- [x] Desktop package preview can import a handover into the current workspace.
- [x] CLI `preview` and `import` commands for verified packages.
- [x] CLI `project export` and `project import` for workspace-aware handover round trips.
- [x] Package tests for successful extraction, tamper rejection, existing destinations and unsafe paths.
- [x] Linux offscreen PySide6 runtime smoke tests pass without shutdown errors.
- [x] Windows, macOS and Linux platform smoke-test matrix, portable PyInstaller bundle builds and wheel/sdist validation.
- [x] Automated core tests and GitHub Actions Python 3.11–3.13 matrix.
- [x] Portable unsigned desktop bundles built successfully on Windows, macOS and Linux in CI.

## Not yet implemented
- [ ] Complete desktop accessibility and keyboard interaction audit, including screen-reader testing, focus visibility, contrast and platform-specific assistive technology.
- [ ] Configurable activity page size, background loading and streaming exports; current UI loads fixed pages of 100 and exports the currently loaded, filtered subset.
- [ ] Import conflict resolution and merge/replace workflows; current inspection is advisory and import always creates a new project.
- [ ] Broader secret coverage, configurable exclusions, and independent validation of secret-scan false positives/negatives.
- [ ] Encryption, signatures and key management.
- [ ] Local/cloud AI adapters and consent UI.
- [ ] Signed Windows, macOS and Linux installers.
- [ ] Independent security review and interactive release qualification.

## Verification
Core tests pass on Python 3.11, 3.12 and 3.13. Offscreen desktop smoke tests and PyInstaller bundle builds passed on Windows, macOS and Linux in run 45603548295. Wheel and source distributions also build and pass Twine metadata checks. The latest accessibility, cursor-pagination and import-inspection changes are undergoing CI verification. Automated CI does not replace interactive manual QA, accessibility validation, signing/notarization or release qualification.
