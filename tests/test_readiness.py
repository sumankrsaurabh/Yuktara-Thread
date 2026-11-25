from yuktara_thread.application.readiness import assess_handover_readiness


def test_readiness_reports_required_gaps_and_recommendations() -> None:
    result = assess_handover_readiness(
        {"summary": ""},
        [],
        [],
        [],
        [],
        [],
        selected_file_count=0,
    )

    assert result["status"] == "incomplete"
    assert result["required_complete"] is False
    assert set(result["missing_required"]) == {
        "project_summary", "goals", "current_state", "handover_notes",
    }
    assert "selected_files" in result["missing_recommended"]
    assert 0 <= result["score"] < 100


def test_readiness_becomes_reviewable_when_required_context_is_present() -> None:
    result = assess_handover_readiness(
        {"summary": "Deliver the first release."},
        [
            {"section_key": "goals", "content": "Ship a stable MVP"},
            {"section_key": "current_state", "content": "Core implementation complete"},
            {"section_key": "handover_notes", "content": "Run tests before release"},
            {"section_key": "scope", "content": "Desktop only"},
            {"section_key": "unresolved_questions", "content": "None"},
        ],
        [{"rationale": "Local-first and transactional"}],
        [{"status": "open", "description": "Finish package import"}],
        [],
        [{"title": "Architecture", "uri": "docs/architecture.md"}],
        selected_file_count=2,
    )

    assert result["status"] == "ready_for_review"
    assert result["required_complete"] is True
    assert result["score"] == 100
    assert result["missing_required"] == []
    assert result["missing_recommended"] == []


def test_readiness_flags_missing_task_and_decision_details() -> None:
    result = assess_handover_readiness(
        {"summary": "Project"},
        [
            {"section_key": "goals", "content": "Goal"},
            {"section_key": "current_state", "content": "In progress"},
            {"section_key": "handover_notes", "content": "Notes"},
        ],
        [{"rationale": ""}],
        [{"status": "blocked", "description": ""}],
        [],
        [],
    )

    assert result["status"] == "needs_attention"
    assert "decision_rationale" in result["missing_recommended"]
    assert "open_task_details" in result["missing_recommended"]
