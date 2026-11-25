# Software Architecture

## Architectural style

Yuktara Thread is a local-first modular monolith. The application is Python-first and runs as a native desktop process. The MVP does not require a server, account, background synchronization service or network connection.

The dependency direction is:

    UI -> Application -> Domain
                 |
                 v
           Infrastructure

Infrastructure implements persistence and package operations used by the application layer. Domain models do not import PySide6, SQLite or ZIP handling.

## Source layout

- src/yuktara_thread/domain/
  - Framework-independent project and context models, validation and domain concepts.
- src/yuktara_thread/application/
  - User-facing use cases and orchestration: workspace, handover, backup, readiness, search, secret scan.
- src/yuktara_thread/infrastructure/database/
  - SQLite connection management, ordered schema migrations and repositories.
- src/yuktara_thread/infrastructure/package.py
  - Portable .thread archive creation, verification, preview and safe extraction.
- src/yuktara_thread/cli/
  - CLI parsing and command-to-use-case mapping.
- src/yuktara_thread/ui/
  - context.py: context editors and revision history.
  - panels.py: intelligence, activity, readiness and dependency graph panels.
  - dialogs.py: search, package preview/import and archived-project recovery.
  - pages.py: project page composition.
  - main_window.py: workspace navigation and application-level UI orchestration.
  - app.py: optional PySide6 bootstrap and first-run workspace selection.
  - styles.py: centralized application styling.
- tests/
  - Domain/application/CLI tests and optional offscreen Qt smoke tests.

## Persistence and transaction rules

- SQLite is the local source of truth.
- Every schema change is a new ordered migration. Never edit an already released migration; add the next version.
- Foreign keys are enabled for each connection. WAL and a bounded busy timeout are configured by the database adapter.
- Repository methods own transaction boundaries for single aggregate mutations.
- A mutation that changes user-visible project state appends its activity event in the same transaction.
- Context updates use optimistic concurrency and append immutable revision snapshots.
- Entity deletion is soft-delete by default. Permanent purge is explicit, dry-run first and leaves an audit event.
- Activity history is append-only by default and is not automatically purged.
- Backup uses SQLite's online backup API; restore publishes to a new destination and never overwrites.

## Application-layer rules

- UI code calls application services or repository-backed use cases; it should not issue SQL directly.
- CLI code validates command arguments and calls the same application use cases as the desktop UI.
- Workspace-aware handover import validates all structured metadata before extracting files or mutating the database.
- Database record restoration is transactional. If it fails after staged extraction, the new extracted directory is removed.
- Do not add a network dependency to core workflows. Any future cloud/AI adapter must require explicit per-operation consent.

## Package trust model

- A .thread package is a ZIP archive with a versioned manifest and SHA-256 file digests.
- Verification proves consistency with the manifest, not publisher identity.
- Packages are not encrypted or signed.
- Imported activity is explicitly marked as imported/unverified.
- Never execute package contents during verification, preview or import.
- Only files in the explicitly selected source directory are eligible for export.

## UI rules

- Keep widgets presentational; validation and state transitions belong in domain/application services.
- Reuse shared dialogs and panels rather than duplicating business workflows.
- Provide clear confirmation for destructive or external actions.
- Use native dialogs for file selection and show recoverable errors without swallowing details.
- Keep keyboard navigation, accessibility labels, high-DPI and resize behavior in release qualification.

## Testing and quality gates

- Core tests run on Python 3.11, 3.12 and 3.13.
- Desktop smoke tests run offscreen on Windows, macOS and Linux.
- Frozen desktop bundles are smoke-built on all three operating systems.
- Wheel and source distributions are built and checked in CI.
- Any change to package metadata, database migrations, retention or recovery requires regression tests for old workspaces and failed-transaction rollback.

## Change procedure

1. Define the user-visible behavior and failure modes.
2. Add or update domain validation and application use cases.
3. Add a migration only when persisted schema changes.
4. Implement CLI and UI adapters against the same use case.
5. Add tests for normal, invalid, recovery and rollback paths.
6. Update architecture, CLI, product status and security documentation.
7. Wait for the complete CI matrix before describing the change as verified.


## Activity timeline pagination

Project activity is ordered newest-first by the composite `(created_at, event_id)` key. The repository accepts an optional exclusive `before` cursor taken from the final row of the previous page. Both fields are required to keep pagination stable when multiple events share a timestamp. The desktop currently requests 100 events per page and loads older pages only after explicit user action. Search, date filters and exports apply to the events currently loaded in the panel; the UI states this limitation. Streaming export and configurable page sizing remain future work.
