from yuktara_thread.application.handover_report import render_handover_report


def test_handover_report_summarizes_verified_package_preview() -> None:
    preview = {
        "format": "yuktara.thread",
        "format_version": 1,
        "project": {"name": "Release plan", "summary": "Prepare the first release."},
        "files": [
            {"path": "src/main.py", "size": 120, "sha256": "a" * 64},
            {"path": "README.md", "size": 80, "sha256": "b" * 64},
        ],
    }

    report = render_handover_report(preview)

    assert "# Handover: Release plan" in report
    assert "Prepare the first release." in report
    assert "- Files: 2" in report
    assert "- Total uncompressed size: 200 bytes" in report
    assert "`README.md` — 80 bytes" in report
    assert "Authenticity: not established" in report


def test_handover_report_handles_empty_package() -> None:
    report = render_handover_report({
        "format": "yuktara.thread",
        "format_version": 1,
        "project": {},
        "files": [],
    })

    assert "# Handover: Unnamed project" in report
    assert "- No files included." in report


def test_report_includes_decision_task_and_dependency_details() -> None:
    report = render_handover_report({
        "format": "yuktara.thread",
        "format_version": 1,
        "project": {
            "name": "Implementation",
            "summary": "Deliver the storage layer.",
            "decisions": [{
                "title": "Choose SQLite", "problem": "Local persistence",
                "selected_option": "SQLite", "rationale": "Transactional",
                "alternatives": ["JSON"], "consequences": "Single local database",
                "status": "accepted",
            }],
            "tasks": [
                {"task_id": "a", "title": "Design schema", "status": "completed", "priority": "high"},
                {"task_id": "b", "title": "Build repository", "status": "open", "priority": "normal"},
            ],
            "task_dependencies": [{"task_id": "b", "depends_on_task_id": "a"}],
            "milestones": [{"title": "MVP", "status": "planned"}],
            "references": [{"title": "Design notes", "reference_type": "document", "uri": "docs/design.md"}],
        },
        "files": [],
    })

    assert "## Decisions" in report
    assert "Rationale: Transactional" in report
    assert "## Tasks" in report
    assert "Build repository depends on Design schema" in report
    assert "## Milestones" in report
    assert "## References" in report
