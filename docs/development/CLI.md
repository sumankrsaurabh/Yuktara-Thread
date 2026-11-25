# Command-Line Interface

The CLI is a lightweight way to exercise package and workspace workflows before the desktop UI is available.

## Package commands

Create a portable package from a directory:

```bash
thread create --input ./project-folder --output ./handover.thread --name "Project name"
```

Verify its manifest and included file hashes without extracting it:

```bash
thread verify ./handover.thread
```

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

Include archived projects:

```bash
thread project list --database ./workspace.sqlite3 --include-archived
```

Archive a project by its ID:

```bash
thread project archive --database ./workspace.sqlite3 --project-id PROJECT_UUID
```

## Desktop application

Install the optional desktop dependency and launch the native workspace:

```bash
python -m pip install -e ".[desktop]"
thread desktop --database ./workspace.sqlite3
```

The equivalent dedicated launcher is `thread-desktop --database ./workspace.sqlite3`. The database path is explicit; the application does not silently create a hidden workspace.

The initial desktop shell includes project selection and creation, structured context editing with revision conflict protection, decision/task/milestone/reference lists with basic create/rename/delete actions, and the project activity timeline. It is an early UI foundation; keyboard accessibility, advanced forms, responsive layouts, package import/export workflows and installer validation remain future work.

## Notes

- The database path is selected by the user; no hidden default workspace is created.
- Workspace commands are local-only and do not make network requests.
- Context editing is currently available through the Python application service, not yet through CLI commands.
- CLI output is JSON for machine-readable project and workspace results.
