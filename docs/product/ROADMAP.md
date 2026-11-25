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
- [x] Decisions, tasks, milestones and references (create/list foundation).
- [x] Append-only events for intelligence entity creation and task dependency changes.
- [x] Task dependency graph with cycle prevention.
- [ ] Full entity update/delete lifecycle and comprehensive event coverage.
- [ ] Project/context events, search, backup and recovery.

## P3 — Desktop MVP
- [ ] PySide6 desktop shell and design system.
- [ ] Project overview, context editor and intelligence screens.
- [ ] Package preview, safe import and handover report.
- [ ] Secret inclusion warnings and readiness checks.
- [ ] Windows/Linux/macOS packaging.

## P4 — Optional intelligence and collaboration
- [ ] Local AI provider adapters.
- [ ] Cloud provider adapters with per-operation approval.
- [ ] Optional encrypted sharing and signing.
- [ ] User-controlled integrations and synchronization.
- [ ] Team governance and audit features.
