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
