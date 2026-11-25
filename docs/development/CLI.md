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
Workspace-aware export includes project metadata, all six context sections, decisions, tasks, milestones, references, task prerequisite edges and up to 1,000 recent activity events. It also includes the explicitly selected files. The export does not include the SQLite database, historical context revision bodies or archived projects.

Import a verified workspace handover into a new project. The destination must be a new directory; the import restores project records and extracts package files there:

```bash
thread project import --database ./recipient.sqlite3 \
  --package ./project-handover.thread \
  --files-destination ./received-project-files
```

Database records are restored in one SQLite transaction. If restoration fails after extraction, the newly created files directory is removed. The recipient gets new local project/entity IDs; the source workspace database is never copied. Current import restores the latest context section contents and current project records. It records the count of source activity events in the import event, but does not replay the original event history or context revision bodies.

## Desktop application

Install the optional desktop dependency and launch the native workspace:

```bash
python -m pip install -e ".[desktop]"
thread desktop --database ./workspace.sqlite3
```

The equivalent dedicated launcher is `thread-desktop --database ./workspace.sqlite3`. The database path is explicit; the application does not silently create a hidden workspace.

The current desktop foundation includes project selection and creation, six structured context editors with revision conflict protection, and tabs for decisions, tasks, milestones, references and project activity. Each intelligence tab supports create, edit and delete; the forms expose the structured fields stored by the domain layer. Deletions are recorded in project history.

The UI remains pre-alpha. Project metadata editing and archive controls are available; archiving retains project data and removes the project from the active list. Task prerequisites can be added and removed from the Tasks tab; the service layer rejects self-links, cross-project links and cycles. Activity supports text search and event-type filtering. The desktop shell can preview verified packages, save a Markdown handover report, extract files to a new folder, or import a package as a new project into the current workspace. The report includes project context, decisions, tasks, milestones, references, dependency details, a deterministic completeness indicator, file inventory and a recipient checklist. The indicator is not a guarantee of correctness or safety, and the report does not prove publisher identity. A dependency graph visualization, archived-project restore UI, activity date-range filters/export, keyboard/accessibility validation and installer validation are not complete.

## Notes

- The database path is selected by the user; no hidden default workspace is created.
- Workspace commands are local-only and do not make network requests.
- Context editing is currently available through the Python application service and desktop UI, not yet through CLI commands.
- CLI output is JSON for machine-readable project and workspace results.
