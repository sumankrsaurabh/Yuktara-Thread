"""Bounded, parameterized search across active workspace project records."""
from __future__ import annotations

from yuktara_thread.application.workspace import WorkspaceService


def search_workspace(
    workspace: WorkspaceService,
    query: str,
    *,
    limit: int = 50,
    include_archived: bool = False,
) -> list[dict]:
    """Search project summaries, context and structured intelligence records."""
    term = query.strip()
    if len(term) < 2:
        raise ValueError("Search query must contain at least 2 characters")
    if len(term) > 200:
        raise ValueError("Search query must not exceed 200 characters")
    if not 1 <= limit <= 100:
        raise ValueError("Search limit must be between 1 and 100")

    statement = """
        SELECT * FROM (
            SELECT p.project_id, p.name AS project_name, 'project' AS entity_type,
                   p.project_id AS entity_id, p.name AS title,
                   substr(p.summary, 1, 240) AS excerpt, p.updated_at
            FROM projects p
            WHERE (? = 1 OR p.status = 'active')
              AND (instr(lower(p.name), lower(?)) > 0
                   OR instr(lower(p.summary), lower(?)) > 0)

            UNION ALL

            SELECT c.project_id, p.name, 'context', c.section_id, c.title,
                   substr(c.content, 1, 240), c.updated_at
            FROM context_sections c JOIN projects p ON p.project_id = c.project_id
            WHERE (? = 1 OR p.status = 'active')
              AND (instr(lower(c.title), lower(?)) > 0
                   OR instr(lower(c.content), lower(?)) > 0)

            UNION ALL

            SELECT d.project_id, p.name, 'decision', d.decision_id, d.title,
                   substr(trim(coalesce(d.problem, '') || ' ' || coalesce(d.rationale, '') ||
                               ' ' || coalesce(d.consequences, '')), 1, 240), d.updated_at
            FROM decisions d JOIN projects p ON p.project_id = d.project_id
            WHERE (? = 1 OR p.status = 'active')
              AND (instr(lower(d.title), lower(?)) > 0
                   OR instr(lower(coalesce(d.problem, '')), lower(?)) > 0
                   OR instr(lower(coalesce(d.selected_option, '')), lower(?)) > 0
                   OR instr(lower(coalesce(d.rationale, '')), lower(?)) > 0
                   OR instr(lower(coalesce(d.consequences, '')), lower(?)) > 0)

            UNION ALL

            SELECT t.project_id, p.name, 'task', t.task_id, t.title,
                   substr(coalesce(t.description, ''), 1, 240), t.updated_at
            FROM tasks t JOIN projects p ON p.project_id = t.project_id
            WHERE (? = 1 OR p.status = 'active')
              AND (instr(lower(t.title), lower(?)) > 0
                   OR instr(lower(coalesce(t.description, '')), lower(?)) > 0
                   OR instr(lower(coalesce(t.owner, '')), lower(?)) > 0)

            UNION ALL

            SELECT m.project_id, p.name, 'milestone', m.milestone_id, m.title,
                   substr(coalesce(m.description, ''), 1, 240), m.updated_at
            FROM milestones m JOIN projects p ON p.project_id = m.project_id
            WHERE (? = 1 OR p.status = 'active')
              AND (instr(lower(m.title), lower(?)) > 0
                   OR instr(lower(coalesce(m.description, '')), lower(?)) > 0)

            UNION ALL

            SELECT r.project_id, p.name, 'reference', r.reference_id, r.title,
                   substr(trim(coalesce(r.uri, '') || ' ' || coalesce(r.notes, '')), 1, 240),
                   r.updated_at
            FROM project_references r JOIN projects p ON p.project_id = r.project_id
            WHERE (? = 1 OR p.status = 'active')
              AND (instr(lower(r.title), lower(?)) > 0
                   OR instr(lower(coalesce(r.uri, '')), lower(?)) > 0
                   OR instr(lower(coalesce(r.notes, '')), lower(?)) > 0)
        )
        ORDER BY updated_at DESC, project_name COLLATE NOCASE, title COLLATE NOCASE
        LIMIT ?
    """
    params = []
    include_flag = 1 if include_archived else 0
    for fields in (2, 2, 5, 3, 2, 3):
        params.append(include_flag)
        params.extend([term] * fields)
    params.append(limit)
    with workspace.database.read() as connection:
        rows = connection.execute(statement, params).fetchall()
    return [dict(row) for row in rows]
