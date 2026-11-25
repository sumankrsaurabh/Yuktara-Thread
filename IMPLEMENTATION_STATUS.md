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
- [x] Automated tests and GitHub Actions Python 3.11–3.13 matrix.

## Not yet implemented
- [ ] Entity-specific soft-delete/restore policy and event retention/export policy.
- [x] Initial PySide6 desktop shell with project navigation, context editor, intelligence list workflows and activity timeline.
- [ ] Desktop UI design-system refinement, accessibility and interaction polish.
- [ ] Package preview and safe transactional import.
- [ ] Human-readable handover report and readiness scoring.
- [ ] Search, backup and recovery workflows.
- [ ] Encryption, signatures and key management.
- [ ] Local/cloud AI adapters and consent UI.
- [ ] Windows, Linux and macOS installers.
- [ ] Independent security review and release qualification.

## Verification
The GitHub Actions workflow tests Python 3.11, 3.12 and 3.13. Check the Actions tab for the latest commit's result; queued or running jobs are not passing results.
