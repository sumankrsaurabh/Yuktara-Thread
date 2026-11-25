# Implementation Status

**Release:** 0.3.1-dev  
**Status:** pre-alpha; not production-ready

## Implemented
- [x] Python package skeleton and CLI.
- [x] Versioned ZIP package writer and SHA-256 integrity verifier.
- [x] SQLite workspace with ordered transactional migrations (schema v1–v2).
- [x] Project create/get/list/update/archive with transactional activity events.
- [x] Six structured context sections with append-only revision snapshots and optimistic concurrency.
- [x] Context revision events in the project timeline.
- [x] Decision, task, milestone and reference create/list/update/delete operations.
- [x] Append-only project event records for project, context, intelligence entity and dependency mutations.
- [x] Task prerequisite relationships with cross-project, self-link and cycle rejection, plus audited edge removal.
- [x] Bounded project activity timeline query.
- [x] Initial PySide6 desktop shell with project navigation, context editor, intelligence tabs and activity timeline.
- [x] Project metadata editing and audited project archiving from the desktop UI.
- [x] Task prerequisite add/remove controls using cycle-safe application services.
- [x] Human-readable activity labels with text search and event-type filtering.
- [x] Structured desktop forms for decision, task, milestone and reference fields.
- [x] Offscreen Qt smoke tests and a dedicated Linux desktop CI job (runtime verification pending latest workflow result; Qt runtime currently constrained to the 6.9 series while investigating a Qt 6.12 offscreen shutdown crash).
- [x] Automated core tests and GitHub Actions Python 3.11–3.13 matrix.

## Not yet implemented
- [ ] Entity-specific soft-delete/restore policy and event retention/export policy.
- [ ] Desktop design-system refinement, accessibility and keyboard interaction audit.
- [ ] Project metadata editing and archive controls in the desktop UI.
- [ ] Task dependency editing and visualization in the desktop UI.
- [ ] Human-readable activity labels, details and filters.
- [ ] Package preview and safe transactional import.
- [ ] Human-readable handover report and readiness scoring.
- [ ] Search, backup and recovery workflows.
- [ ] Encryption, signatures and key management.
- [ ] Local/cloud AI adapters and consent UI.
- [ ] Windows, Linux and macOS installers.
- [ ] Independent security review and release qualification.

## Verification
Core automated tests run on Python 3.11, 3.12 and 3.13. The desktop job installs PySide6 and Qt runtime libraries and runs the UI offscreen on Linux. A passing workflow is required before claiming runtime verification; this CI job does not replace Windows/macOS testing or interactive manual QA.
