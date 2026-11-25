from pathlib import Path

import pytest

from yuktara_thread.domain.models import ProjectContext
from yuktara_thread.infrastructure.package import PackageError, create_package, verify_package


def test_create_and_verify_package(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (source / "notes.md").write_text("# Handover\nImportant context.", encoding="utf-8")
    output = tmp_path / "handover.thread"

    project = ProjectContext.create("Example Project", "A test project")
    create_package(source, output, project.to_dict())

    result = verify_package(output)
    assert result["valid"] is True
    assert result["file_count"] == 1
    assert result["project"]["name"] == "Example Project"


def test_tampered_package_fails_verification(tmp_path: Path) -> None:
    source = tmp_path / "project"
    source.mkdir()
    (source / "notes.md").write_text("original", encoding="utf-8")
    output = tmp_path / "handover.thread"
    create_package(source, output, ProjectContext.create("Example").to_dict())

    import zipfile
    replacement = tmp_path / "tampered.thread"
    with zipfile.ZipFile(output, "r") as src, zipfile.ZipFile(replacement, "w") as dst:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename == "files/notes.md":
                data = b"changed"
            dst.writestr(item, data)

    with pytest.raises(PackageError, match="SHA-256 mismatch"):
        verify_package(replacement)


def test_missing_package_fails(tmp_path: Path) -> None:
    with pytest.raises(PackageError, match="does not exist"):
        verify_package(tmp_path / "missing.thread")
