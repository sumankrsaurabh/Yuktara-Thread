"""Small shared helper for append-only project activity events."""
from __future__ import annotations
import json
from uuid import uuid4


def append_project_event(connection, *, project_id: str, event_type: str,
                         entity_type: str, entity_id: str | None,
                         payload: dict[str, object], created_at: str) -> None:
    """Insert a curated event using the caller's transaction."""
    connection.execute(
        """INSERT INTO project_events
           (event_id, project_id, event_type, entity_type, entity_id, payload_json, created_at)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (str(uuid4()), project_id, event_type, entity_type, entity_id,
         json.dumps(payload, ensure_ascii=False, sort_keys=True), created_at),
    )
