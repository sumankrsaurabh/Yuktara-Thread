# Changelog

## 0.5.0.dev0 — Privacy, recovery and search foundation

- Add local heuristic secret review before CLI and desktop handover export, with explicit acknowledgement when findings exist.
- Add SQLite online workspace backup and validated restore into a new database path, available in the CLI and desktop shell.
- Add bounded workspace-wide search for project summaries, context sections, decisions, tasks, milestones and references, with CLI and desktop entry points.
- Validate backup integrity, foreign-key consistency, required workspace tables and migration history before publishing restored data.

## 0.4.0.dev0 — Workspace-aware handover and privacy review

- Export complete workspace context, decisions, tasks, milestones, references, task prerequisites and recent activity metadata into `.thread` packages.
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
