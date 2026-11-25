"""Ordered, transactional SQLite schema migrations."""
from __future__ import annotations
import sqlite3

MIGRATIONS: dict[int, tuple[str, ...]] = {
    1: (
        """CREATE TABLE projects (
            project_id TEXT PRIMARY KEY, name TEXT NOT NULL CHECK(length(trim(name)) > 0),
            summary TEXT NOT NULL DEFAULT '', status TEXT NOT NULL DEFAULT 'active'
            CHECK(status IN ('active', 'archived')), created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL, archived_at TEXT
        )""",
        "CREATE INDEX idx_projects_status_updated ON projects(status, updated_at DESC)",
        """CREATE TABLE context_sections (
            section_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            section_key TEXT NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL DEFAULT '',
            revision INTEGER NOT NULL DEFAULT 1 CHECK(revision > 0), updated_at TEXT NOT NULL,
            UNIQUE(project_id, section_key)
        )""",
        """CREATE TABLE context_revisions (
            revision_id TEXT PRIMARY KEY, section_id TEXT NOT NULL REFERENCES context_sections(section_id) ON DELETE CASCADE,
            revision INTEGER NOT NULL, title TEXT NOT NULL, content TEXT NOT NULL,
            created_at TEXT NOT NULL, UNIQUE(section_id, revision)
        )""",
        "CREATE INDEX idx_context_revisions_section ON context_revisions(section_id, revision DESC)",
    ),
    2: (
        """CREATE TABLE project_events (
            event_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            event_type TEXT NOT NULL, entity_type TEXT NOT NULL, entity_id TEXT,
            payload_json TEXT NOT NULL DEFAULT '{}', created_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_project_events_timeline ON project_events(project_id, created_at DESC, event_id)",
        """CREATE TABLE decisions (
            decision_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0), problem TEXT NOT NULL DEFAULT '',
            selected_option TEXT NOT NULL DEFAULT '', alternatives_json TEXT NOT NULL DEFAULT '[]',
            rationale TEXT NOT NULL DEFAULT '', consequences TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'proposed' CHECK(status IN ('proposed','accepted','rejected','superseded')),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_decisions_project ON decisions(project_id, updated_at DESC)",
        """CREATE TABLE tasks (
            task_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0), description TEXT NOT NULL DEFAULT '',
            status TEXT NOT NULL DEFAULT 'open' CHECK(status IN ('open','in_progress','blocked','completed','cancelled')),
            priority TEXT NOT NULL DEFAULT 'normal' CHECK(priority IN ('low','normal','high','critical')),
            owner TEXT NOT NULL DEFAULT '', due_at TEXT, created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_tasks_project_status ON tasks(project_id, status, updated_at DESC)",
        """CREATE TABLE task_dependencies (
            task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            depends_on_task_id TEXT NOT NULL REFERENCES tasks(task_id) ON DELETE CASCADE,
            created_at TEXT NOT NULL, PRIMARY KEY(task_id, depends_on_task_id), CHECK(task_id <> depends_on_task_id)
        )""",
        """CREATE TABLE milestones (
            milestone_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0), description TEXT NOT NULL DEFAULT '',
            due_at TEXT, status TEXT NOT NULL DEFAULT 'planned'
            CHECK(status IN ('planned','in_progress','completed','cancelled')),
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_milestones_project ON milestones(project_id, due_at, updated_at DESC)",
        """CREATE TABLE project_references (
            reference_id TEXT PRIMARY KEY, project_id TEXT NOT NULL REFERENCES projects(project_id) ON DELETE CASCADE,
            title TEXT NOT NULL CHECK(length(trim(title)) > 0), reference_type TEXT NOT NULL DEFAULT 'other'
            CHECK(reference_type IN ('document','repository','website','issue','person','other')),
            uri TEXT NOT NULL DEFAULT '', notes TEXT NOT NULL DEFAULT '',
            created_at TEXT NOT NULL, updated_at TEXT NOT NULL
        )""",
        "CREATE INDEX idx_references_project ON project_references(project_id, created_at DESC)",
    ),
    3: (
        "ALTER TABLE decisions ADD COLUMN deleted_at TEXT",
        "ALTER TABLE tasks ADD COLUMN deleted_at TEXT",
        "ALTER TABLE milestones ADD COLUMN deleted_at TEXT",
        "ALTER TABLE project_references ADD COLUMN deleted_at TEXT",
        "CREATE INDEX idx_decisions_deleted ON decisions(project_id, deleted_at)",
        "CREATE INDEX idx_tasks_deleted ON tasks(project_id, deleted_at)",
        "CREATE INDEX idx_milestones_deleted ON milestones(project_id, deleted_at)",
        "CREATE INDEX idx_references_deleted ON project_references(project_id, deleted_at)",
    )
}


def apply_migrations(connection: sqlite3.Connection) -> int:
    """Apply pending migrations and return current schema version."""
    connection.execute("""CREATE TABLE IF NOT EXISTS schema_migrations (
        version INTEGER PRIMARY KEY, applied_at TEXT NOT NULL
    )""")
    row = connection.execute("SELECT COALESCE(MAX(version), 0) AS version FROM schema_migrations").fetchone()
    current = int(row["version"])
    latest = max(MIGRATIONS, default=0)
    if current > latest:
        raise RuntimeError(f"Database schema version {current} is newer than this application supports ({latest})")
    for version in sorted(MIGRATIONS):
        if version <= current:
            continue
        if version != current + 1:
            raise RuntimeError(f"Missing migration after schema version {current}")
        for statement in MIGRATIONS[version]:
            connection.execute(statement)
        from datetime import datetime, timezone
        connection.execute("INSERT INTO schema_migrations(version, applied_at) VALUES (?, ?)",
                           (version, datetime.now(timezone.utc).isoformat()))
        current = version
    return current
