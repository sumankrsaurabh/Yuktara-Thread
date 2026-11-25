from pathlib import Path

import pytest

from yuktara_thread.domain.models import ProjectContext
from yuktara_thread.infrastructure.package import (
    PackageError, _safe_archive_name, create_package, import_package, preview_package, verify_package,
)


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
                data = b"tampered"
            dst.writestr(item, data)

    with pytest.raises(PackageError, match="SHA-256 mismatch"):
        verify_package(replacement)


def test_missing_package_fails(tmp_path: Path) -> None:
    with pytest.raises(PackageError, match="does not exist"):
        verify_package(tmp_path / "missing.thread")


def test_preview_lists_verified_files_without_extracting(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.md").write_text("handover notes", encoding="utf-8")
    (source / "docs").mkdir()
    (source / "docs" / "plan.txt").write_text("implementation plan", encoding="utf-8")
    package = tmp_path / "handover.thread"
    create_package(source, package, ProjectContext.create("Preview project").to_dict())

    preview = preview_package(package)

    assert preview["valid"] is True
    assert preview["file_count"] == 2
    assert [item["path"] for item in preview["files"]] == ["docs/plan.txt", "notes.md"]
    assert not (tmp_path / "files").exists()


def test_import_package_publishes_verified_files(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.md").write_text("handover notes", encoding="utf-8")
    (source / "docs").mkdir()
    (source / "docs" / "plan.txt").write_text("implementation plan", encoding="utf-8")
    package = tmp_path / "handover.thread"
    create_package(source, package, ProjectContext.create("Import project").to_dict())

    destination = import_package(package, tmp_path / "imported-project")

    assert (destination / "files" / "notes.md").read_text(encoding="utf-8") == "handover notes"
    assert (destination / "files" / "docs" / "plan.txt").read_text(encoding="utf-8") == "implementation plan"
    assert not list(tmp_path.glob(".imported-project.thread-*"))
    assert not (tmp_path / ".imported-project.thread-import.lock").exists()


def test_import_refuses_existing_destination_without_modifying_it(tmp_path: Path) -> None:
    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.md").write_text("safe", encoding="utf-8")
    package = tmp_path / "handover.thread"
    create_package(source, package, ProjectContext.create("Existing destination").to_dict())
    destination = tmp_path / "existing"
    destination.mkdir()
    sentinel = destination / "keep.txt"
    sentinel.write_text("do not overwrite", encoding="utf-8")

    with pytest.raises(PackageError, match="already exists"):
        import_package(package, destination)

    assert sentinel.read_text(encoding="utf-8") == "do not overwrite"


def test_import_rejects_tampered_package_without_partial_output(tmp_path: Path) -> None:
    import zipfile

    source = tmp_path / "source"
    source.mkdir()
    (source / "notes.md").write_text("original", encoding="utf-8")
    package = tmp_path / "handover.thread"
    create_package(source, package, ProjectContext.create("Tamper test").to_dict())
    tampered = tmp_path / "tampered.thread"
    with zipfile.ZipFile(package, "r") as original, zipfile.ZipFile(tampered, "w") as changed:
        for entry in original.infolist():
            content = original.read(entry.filename)
            if entry.filename == "files/notes.md":
                content = b"tampered"
            changed.writestr(entry, content)

    destination = tmp_path / "should-not-exist"
    with pytest.raises(PackageError, match="SHA-256 mismatch"):
        import_package(tampered, destination)

    assert not destination.exists()
    assert not list(tmp_path.glob(".should-not-exist.thread-*"))


@pytest.mark.parametrize(
    "archive_path",
    [
        "../outside.txt",
        "files/../outside.txt",
        "files//double-separator.txt",
        "files/CON.txt",
        "files/LPT1.log",
        "files/unsafe?.txt",
        "C:/outside.txt",
        "files\\\\backslash.txt",
    ],
)
def test_archive_paths_reject_traversal_and_platform_unsafe_names(archive_path: str) -> None:
    with pytest.raises(PackageError):
        _safe_archive_name(archive_path)
