# Product Roadmap

## P0 — Portable package foundation
- [x] Package format prototype and verifier.
- [x] CLI create and verify commands.
- [x] Initial test suite and CI workflow.

## P1 — Workspace Core (0.2)
- [x] SQLite connection and transactional migrations.
- [x] Project create/get/list/update/archive.
- [x] Structured context sections and revision history.
- [x] Optimistic concurrency for context editing.

## P2 — Project Intelligence Core (0.3)
- [x] Decisions, tasks, milestones and references.
- [x] Create/list/update/delete lifecycle.
- [x] Transactional activity events for project, context and intelligence mutations.
- [x] Task dependency graph with cycle prevention.
- [x] Entity soft-delete/restore with audited lifecycle events.
- [ ] Retention/purge policy and event export.
- [x] Bounded local search across project summaries, context and intelligence records.
- [x] Consistent SQLite backup and validated restore into a new workspace database.
- [ ] Advanced recovery, restore points and search filters.
- [x] Consistent SQLite backup and integrity-checked restore into a new workspace database.

## P3 — Desktop MVP
- [x] Initial PySide6 desktop shell and workspace navigation.
- [x] Context editor and activity timeline.
- [x] Structured create/edit forms for decisions, tasks, milestones and references.
- [x] Project metadata editing and audited archive control.
- [x] Task prerequisite add/remove controls.
- [x] Human-readable activity labels, text search and event-type filters.
- [x] Linux offscreen desktop runtime smoke tests.
- [x] Verified package preview and staged safe file extraction (CLI and desktop).
- [x] Archived-project restore UI and audited application/CLI restoration.
- [ ] Task dependency graph visualization.
- [ ] Activity date-range filters and export.
- [ ] Desktop design-system refinement and accessibility.
- [x] Workspace-aware package export/import for context, decisions, tasks, milestones, references and task dependencies.
- [x] Markdown handover report and recipient-side import workflow.
- [ ] Full source activity-history replay and historical context revision-body export.
- [x] Human-readable handover report with decisions, tasks, milestones, references and context.
- [x] Deterministic handover readiness checks and report indicator.
- [x] Secret inclusion warnings and inclusion review.
- [ ] Windows/Linux/macOS packaging and platform QA.

## P4 — Optional intelligence and collaboration
- [ ] Local AI provider adapters.
- [ ] Cloud provider adapters with per-operation approval.
- [ ] Optional encrypted sharing and signing.
- [ ] User-controlled integrations and synchronization.
- [ ] Team governance and audit features.
