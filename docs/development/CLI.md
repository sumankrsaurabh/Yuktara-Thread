# Command-Line Interface

The CLI is a lightweight way to exercise package and workspace workflows.

## Package commands

Create a portable package from a directory:

```bash
thread create --input ./project-folder --output ./handover.thread --name "Project name"
```

Verify its manifest and included file hashes without extracting it:

```bash
thread verify ./handover.thread
```

Inspect project metadata and the verified file list without extracting:

```bash
thread preview ./handover.thread
```

Safely extract verified files into a new directory (existing destinations are never overwritten):

```bash
thread import ./handover.thread --destination ./handover-import
```

Import uses a temporary staging directory, checks the manifest and each extracted file's size and SHA-256 digest, then publishes the completed directory. On failure, staging files are removed. The basic `thread create` command contains project metadata and files. Workspace-aware `thread project export` additionally serializes context sections, decisions, tasks, milestones, references, task prerequisites and recent activity.

## Search

Search active projects and their context, decisions, tasks, milestones and references:

```bash
thread search --database ./workspace.sqlite3 --query "shader cache" --limit 50
```

Archived projects are excluded by default. Include them explicitly with `--include-archived`. Search is local, parameterized and bounded to 100 results; query length is limited to 2–200 characters.

## Workspace commands

Initialize a local SQLite workspace:

```bash
thread workspace init --database ./workspace.sqlite3
```

Create a project:

```bash
thread project create --database ./workspace.sqlite3 --name "Project name" --summary "Short summary"
```

List active projects:

```bash
thread project list --database ./workspace.sqlite3
```

Create a consistent, integrity-checked SQLite snapshot. The output path must be new; existing files are never overwritten:

```bash
thread workspace backup --database ./workspace.sqlite3 --output ./workspace.backup
```

Restore a valid backup into a separate, new database file:

```bash
thread workspace restore --backup ./workspace.backup --database ./restored-workspace.sqlite3
```

Backup uses SQLite's online backup API, so committed data in the WAL is included consistently. Restore validates SQLite integrity, foreign-key constraints, migration history and required workspace tables before publishing the new file. It never replaces an existing database. Backups are not encrypted; protect them as carefully as the original workspace.

Include archived projects:

```bash
thread project list --database ./workspace.sqlite3 --include-archived
```

Archive a project by its ID:

```bash
thread project archive --database ./workspace.sqlite3 --project-id PROJECT_UUID
```

Restore an archived project without recreating its records or activity history:

```bash
thread project restore --database ./workspace.sqlite3 --project-id PROJECT_UUID
```

The restore command only accepts archived projects. It returns the original project to the active list and appends a `project.restored` activity event.

## Recover deleted project records

Decisions, tasks, milestones and references use soft deletion. Normal record lists omit deleted items; their IDs and data remain in the local database until a future retention/purge policy is introduced.

List deleted tasks in a project:

```bash
thread record list-deleted --database ./workspace.sqlite3 \
  --project-id PROJECT_UUID --entity-type task
```

Restore a deleted task (the entity type can also be `decision`, `milestone` or `reference`):

```bash
thread record restore --database ./workspace.sqlite3 \
  --project-id PROJECT_UUID --entity-type task --entity-id ENTITY_UUID
```

Restore preserves the original entity ID and appends a `task.restored` (or corresponding entity type) event. Task prerequisite edges remain in place while a task is deleted; dependency creation rejects deleted tasks.

Preview which deleted tasks are older than 30 days (dry-run; no records are removed):

```bash
thread record purge-deleted --database ./workspace.sqlite3 \
  --project-id PROJECT_UUID --entity-type task --older-than-days 30
```

After reviewing the eligible count, permanently purge those records with explicit confirmation:

```bash
thread record purge-deleted --database ./workspace.sqlite3 \
  --project-id PROJECT_UUID --entity-type task --older-than-days 30 --confirm
```

Purging is never automatic. The operation removes only soft-deleted records older than the requested age and appends a permanent `task.purged` audit event. Deleting a task also removes its prerequisite edges through SQLite foreign-key cascades. Activity events are retained indefinitely by default.

Export a complete workspace project as a `.thread` handover package. The selected files directory is explicit; only files inside that directory are included:

```bash
thread project export --database ./workspace.sqlite3 --project-id PROJECT_UUID \
  --files ./selected-handover-files --output ./project-handover.thread
```

Before export, the CLI scans selected regular files locally for common credential and private-key patterns. If it finds possible secrets, it prints only file paths, line numbers and rule names, then stops without creating a package. Review the findings and remove secrets where possible. To proceed intentionally after review:

```bash
thread project export --database ./workspace.sqlite3 --project-id PROJECT_UUID \
  --files ./selected-handover-files --output ./project-handover.thread \
  --allow-potential-secrets
```

The scan is heuristic: it can produce false positives and cannot guarantee that files contain no secrets. It does not print matched values, call a network service or use AI. Files larger than 1 MB, non-UTF-8/binary files and files beyond scan limits are skipped and reported in the scan result.
Workspace-aware export includes project metadata, all six context sections and their revision bodies, decisions, tasks, milestones, references, task prerequisite edges and up to 1,000 recent activity events. It also includes the explicitly selected files. The export does not include the SQLite database or archived projects. It carries context revision snapshots so recipients can inspect and restore earlier context as a new revision.

Import a verified workspace handover into a new project. The destination must be a new directory; the import restores project records and extracts package files there:

```bash
thread project import --database ./recipient.sqlite3 \
  --package ./project-handover.thread \
  --files-destination ./received-project-files
```

Database records are restored in one SQLite transaction. The workspace keeps a durable import journal with the package manifest hash, destination, project ID and import state. Project creation and the `database_committed` journal state are committed atomically. If restoration fails after extraction, the newly created files directory is removed when possible; if cleanup fails, the journal records that manual recovery is required. The recipient gets new local project/entity IDs; the source workspace database is never copied. Current import restores the latest context section contents and current project records. It restores the included context revision bodies and replays up to 1,000 validated source activity events. Replayed events retain their original timestamps and are marked as imported in payload metadata; they are not cryptographically authenticated and must not be treated as proof of who performed the original actions.

Reconcile interrupted workspace imports without deleting files or project data:

```bash
thread import-recovery --database ./recipient.sqlite3
```

The command finalizes journal entries when both the imported project and extracted directory exist. If neither exists, it marks the attempt failed. If only one exists, it marks the attempt `recovery_required` and reports the mismatch for manual review. Reconciliation is explicit and safe to repeat; it skips attempts updated within the previous five minutes to avoid racing a live import, and it does not automatically remove directories or project records.

## Desktop application

Install the optional desktop dependency and launch the native workspace:

```bash
python -m pip install -e ".[desktop]"
thread desktop --database ./workspace.sqlite3
```

The equivalent dedicated launcher is `thread-desktop --database ./workspace.sqlite3`. You can also run `thread-desktop` without arguments; the desktop application then asks whether to open an existing workspace or create a new database. It never selects a hidden default workspace. When creating a workspace, the chosen destination must be a new file.

The current desktop foundation includes project selection and creation, six structured context editors with revision conflict protection and a history viewer that can restore older content as a new revision, and tabs for decisions, tasks, milestones, references and project activity. Each intelligence tab supports create, edit and delete; the forms expose the structured fields stored by the domain layer. Deletions are soft-deleted in the service layer and recorded in project history. Deleted-record recovery is available through both the CLI and a dedicated desktop dialog.

The UI remains pre-alpha. Project metadata editing and archive controls are available; archiving retains project data and removes the project from the active list. Task prerequisites can be added and removed from the Tasks tab; the service layer rejects self-links, cross-project links and cycles. Activity supports text search, event-type filtering, inclusive date-range filtering and export of the visible event set to JSON or Markdown. Deleted records can be reviewed and restored from each intelligence tab; edits to a deleted record are blocked until it is restored. The desktop shell can preview verified packages, save a Markdown handover report, extract files to a new folder, or import a package as a new project into the current workspace. The report includes project context, decisions, tasks, milestones, references, dependency details, a deterministic completeness indicator, file inventory and a recipient checklist. The indicator is not a guarantee of correctness or safety, and the report does not prove publisher identity. The Tasks tab includes a read-only layered dependency map. Keyboard/accessibility validation and installer validation are not complete.

## Notes

- The database path is selected by the user; no hidden default workspace is created.
- Workspace commands are local-only and do not make network requests.
- Context editing is currently available through the Python application service and desktop UI, not yet through CLI commands.
- CLI output is JSON for machine-readable project and workspace results.
