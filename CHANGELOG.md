# Changelog

## 0.4.0.dev0 — Workspace-aware handover

- Export complete workspace context, decisions, tasks, milestones, references, task prerequisites and recent activity metadata into `.thread` packages.
- Restore verified handovers into a new local workspace with fresh IDs and dependency remapping.
- Add desktop package preview, workspace import and Markdown handover report export.
- Harden package creation with strict JSON metadata, isolated temporary files and post-write verification.
- Add import validation and transactional database restoration.

This remains a pre-alpha development version. It is not a production release.

## 0.1.0 — Initial foundation

- Establish Python package and repository conventions.
- Add portable ZIP package creation and integrity verification.
- Add CLI entry points and package tests.
- Add product, architecture, security and implementation-status documents.

This is a pre-alpha engineering foundation, not a production release.
