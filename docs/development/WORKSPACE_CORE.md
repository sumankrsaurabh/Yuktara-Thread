# Workspace Core — 0.2

## Implemented

- SQLite connection wrapper with foreign keys, WAL and busy timeout.
- Transaction boundary and ordered migration runner.
- Project create/get/list/update/archive repository operations.
- Six structured context sections created with each project.
- Context revision snapshots and optimistic concurrency checks.
- Application-level `WorkspaceService` façade.
- Integration tests for migration, CRUD, archive, context history and stale writes.

## Deliberate limitations

- No desktop UI in this increment.
- No project event stream yet.
- No full-text search or multi-user locking protocol.
- No automatic backup/restore.
- No import of older databases or migration from any pre-release local data.
- Database schema currently starts at version 1; this is a new workspace schema, not a migration of any pre-existing user database.

## Example

```python
from pathlib import Path
from yuktara_thread.application.workspace import WorkspaceService

workspace = WorkspaceService(Path.home() / ".yuktara-thread" / "workspace.sqlite3")
project = workspace.create_project("Website redesign", "Customer portal refresh")
sections = workspace.get_context(project.project_id)
goals = next(section for section in sections if section.section_key == "goals")
workspace.save_context(
    project.project_id, "goals", "Deliver accessible responsive UI",
    expected_revision=goals.revision,
)
```
