# Workspace Database

## Engine and ownership

The MVP uses one SQLite database per local workspace. The application layer owns initialization and repository coordination. Presentation code must never issue SQL directly.

## Migration policy

- Schema changes are ordered integer migrations.
- Each migration is applied inside a transaction.
- Statements are executed individually; do not use `sqlite3.executescript()` inside the migration transaction.
- Never edit a migration that may already have been applied. Add a new migration instead.
- Record applied versions in `schema_migrations`.

## Version 1 schema

- `projects`: project identity, name, summary, active/archive state and timestamps.
- `context_sections`: one structured section per project and supported key.
- `context_revisions`: append-only snapshots created when a section is updated.

## Version 2 schema

- `project_events`: append-only event records with curated JSON payloads.
- `decisions`: problem, selected option, alternatives, rationale, consequences and lifecycle status.
- `tasks`: status, priority, owner and optional due date.
- `task_dependencies`: directed prerequisite edges; self-links and cycles are rejected by the repository.
- `milestones`: dated project checkpoints and status.
- `project_references`: typed URI or local reference metadata.

## Event policy

Events are inserted in the same database transaction as the operation they describe. Current coverage includes project create/update/archive, context saves, intelligence entity create/update/delete, and task dependency additions. Payloads are curated and must never contain credentials, secrets or raw file contents. Event rows are append-only at the repository layer; physical deletion of a project cascades its events, so project deletion is not exposed as a user operation.

Entity deletion currently physically removes the entity row while preserving a minimal deletion event. A future retention/export policy and soft-delete/restore semantics remain open design work.

## Concurrency

Context saves use optimistic concurrency: callers provide the revision they originally loaded. A stale revision is rejected instead of overwriting a newer edit.

## Backups and recovery

Database backup/restore, corruption recovery and schema downgrade are not implemented. Users should keep independent backups of important workspace data.
