from pathlib import Path

from yuktara_thread.application.secret_scan import scan_selected_files


def test_scan_reports_likely_secret_without_returning_secret_value(tmp_path: Path) -> None:
    source = tmp_path / "selected"
    source.mkdir()
    secret = "ghp_" + "A" * 36
    (source / "settings.txt").write_text(
        f"safe=true\nGITHUB_TOKEN={secret}\n", encoding="utf-8"
    )
    result = scan_selected_files(source)

    assert result["finding_count"] >= 1
    assert any(
        item["path"] == "settings.txt" and item["line"] == 2
        and item["rule"] == "github-token"
        for item in result["findings"]
    )
    assert secret not in repr(result)


def test_scan_flags_sensitive_filenames_and_private_key_headers(tmp_path: Path) -> None:
    source = tmp_path / "selected"
    source.mkdir()
    (source / ".env").write_text("APP_MODE=production\n", encoding="utf-8")
    (source / "key.txt").write_text(
        "-----BEGIN PRIVATE KEY-----\nplaceholder\n", encoding="utf-8"
    )

    result = scan_selected_files(source)

    assert any(item["rule"] == "sensitive-filename" for item in result["findings"])
    assert any(item["rule"] == "private-key" for item in result["findings"])


def test_scan_skips_binary_and_oversized_files(tmp_path: Path) -> None:
    source = tmp_path / "selected"
    source.mkdir()
    (source / "image.bin").write_bytes(b"\x00\xffsecret")
    (source / "large.txt").write_bytes(b"x" * 1_000_001)

    result = scan_selected_files(source)

    assert result["finding_count"] == 0
    assert {item["reason"] for item in result["skipped"]} == {"file-size-limit"}
    assert result["scanned_files"] == 1


def test_scan_requires_existing_directory(tmp_path: Path) -> None:
    try:
        scan_selected_files(tmp_path / "missing")
    except ValueError as exc:
        assert "existing directory" in str(exc)
    else:
        raise AssertionError("Expected ValueError")


def test_scan_detects_generic_password_assignment_without_disclosing_value(tmp_path: Path) -> None:
    source = tmp_path / "selected"
    source.mkdir()
    password = "example-password-value"
    (source / "config.txt").write_text(
        f"password={password}", encoding="utf-8"
    )

    result = scan_selected_files(source)

    assert any(item["rule"] == "generic-secret-assignment" for item in result["findings"])
    assert password not in repr(result)
