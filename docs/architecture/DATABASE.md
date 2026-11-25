# Workspace Database

## Engine and ownership

The MVP uses one SQLite database per local workspace. The application layer owns initialization and repository coordination. Presentation code must never issue SQL directly.

## Migration policy

- Schema changes are ordered integer migrations.
- Each migration is applied inside a transaction.
- Statements are executed individually; do not use `sqlite3.executescript()` inside the migration transaction because it may implicitly commit.
- Never edit a migration that may already have been applied to a user's database. Add a new migration instead.
- Record applied versions in `schema_migrations`.

## Version 1 schema

- `projects`: project identity, name, summary, active/archive state and timestamps.
- `context_sections`: one structured section per project and supported key.
- `context_revisions`: append-only snapshots created when a section is updated.

## Concurrency

Context saves use optimistic concurrency: callers provide the revision they originally loaded. A stale revision is rejected instead of overwriting a newer edit.

## Backups and recovery

Database backup/restore, corruption recovery and schema downgrade are not implemented in this milestone. Users should keep independent backups of important workspace data.
