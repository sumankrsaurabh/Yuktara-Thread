from pathlib import Path
import json

from yuktara_thread.cli.main import main


def test_workspace_and_project_cli(tmp_path: Path, capsys) -> None:
    database = tmp_path / "cli.sqlite3"
    assert main(["workspace", "init", "--database", str(database)]) == 0
    initialized = json.loads(capsys.readouterr().out)
    assert initialized["initialized"] is True

    assert main(["project", "create", "--database", str(database),
                 "--name", "CLI Project", "--summary", "Created from CLI"]) == 0
    created = json.loads(capsys.readouterr().out)
    assert created["name"] == "CLI Project"

    assert main(["project", "list", "--database", str(database)]) == 0
    projects = json.loads(capsys.readouterr().out)
    assert len(projects) == 1
    assert projects[0]["project_id"] == created["project_id"]


def test_desktop_cli_requires_explicit_workspace_database(tmp_path: Path) -> None:
    from yuktara_thread.cli.main import build_parser

    database = tmp_path / "desktop.sqlite3"
    args = build_parser().parse_args(["desktop", "--database", str(database)])
    assert args.command == "desktop"
    assert args.database == database


def test_package_preview_and_import_cli(tmp_path: Path, capsys) -> None:
    from yuktara_thread.domain.models import ProjectContext
    from yuktara_thread.infrastructure.package import create_package

    source = tmp_path / "source"
    source.mkdir()
    (source / "handover.md").write_text("Next: implement preview.", encoding="utf-8")
    package = tmp_path / "handover.thread"
    create_package(source, package, ProjectContext.create("CLI handover").to_dict())

    assert main(["preview", str(package)]) == 0
    preview = json.loads(capsys.readouterr().out)
    assert preview["valid"] is True
    assert preview["files"][0]["path"] == "handover.md"

    destination = tmp_path / "imported"
    assert main(["import", str(package), "--destination", str(destination)]) == 0
    imported = json.loads(capsys.readouterr().out)
    assert imported["imported"] is True
    assert (destination / "files" / "handover.md").read_text(encoding="utf-8") == "Next: implement preview."


def test_project_export_cli_includes_workspace_context(tmp_path: Path, capsys) -> None:
    database = tmp_path / "export.sqlite3"
    files = tmp_path / "selected"
    files.mkdir()
    (files / "brief.md").write_text("A brief", encoding="utf-8")
    assert main(["workspace", "init", "--database", str(database)]) == 0
    capsys.readouterr()
    assert main(["project", "create", "--database", str(database), "--name", "Export CLI"]) == 0
    project = json.loads(capsys.readouterr().out)

    assert main([
        "project", "export", "--database", str(database),
        "--project-id", project["project_id"], "--files", str(files),
        "--output", str(tmp_path / "export.thread"),
    ]) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["exported"] is True
    assert (tmp_path / "export.thread").is_file()


def test_project_import_cli_restores_handover_into_workspace(tmp_path: Path, capsys) -> None:
    from yuktara_thread.application.workspace import WorkspaceService

    source_db = tmp_path / "source.sqlite3"
    selected = tmp_path / "selected"
    selected.mkdir()
    (selected / "guide.md").write_text("Read me first", encoding="utf-8")
    assert main(["workspace", "init", "--database", str(source_db)]) == 0
    capsys.readouterr()
    assert main(["project", "create", "--database", str(source_db), "--name", "CLI round trip"]) == 0
    source_project = json.loads(capsys.readouterr().out)
    source_workspace = WorkspaceService(source_db)
    source_workspace.intelligence.create_task(
        source_project["project_id"], title="Review imported data"
    )
    package = tmp_path / "roundtrip.thread"
    assert main([
        "project", "export", "--database", str(source_db),
        "--project-id", source_project["project_id"], "--files", str(selected),
        "--output", str(package),
    ]) == 0
    capsys.readouterr()

    receiving_db = tmp_path / "receiving.sqlite3"
    files_destination = tmp_path / "received-files"
    assert main([
        "project", "import", "--database", str(receiving_db),
        "--package", str(package), "--files-destination", str(files_destination),
    ]) == 0
    imported = json.loads(capsys.readouterr().out)
    receiving_workspace = WorkspaceService(receiving_db)

    assert imported["imported"] is True
    assert imported["name"] == "CLI round trip"
    restored = receiving_workspace.list_projects()
    assert len(restored) == 1
    assert receiving_workspace.intelligence.list_records(restored[0].project_id, "task")[0]["title"] == "Review imported data"
    assert (files_destination / "files" / "guide.md").read_text(encoding="utf-8") == "Read me first"


def test_project_export_requires_explicit_override_for_potential_secrets(tmp_path: Path, capsys) -> None:
    database = tmp_path / "secret-export.sqlite3"
    files = tmp_path / "selected-secret-files"
    files.mkdir()
    token = "ghp_" + "B" * 36
    (files / "settings.txt").write_text(
        f"GITHUB_TOKEN={token}\\n", encoding="utf-8"
    )
    assert main(["workspace", "init", "--database", str(database)]) == 0
    capsys.readouterr()
    assert main(["project", "create", "--database", str(database), "--name", "Secret review"]) == 0
    project = json.loads(capsys.readouterr().out)
    package = tmp_path / "blocked.thread"
    args = [
        "project", "export", "--database", str(database),
        "--project-id", project["project_id"], "--files", str(files),
        "--output", str(package),
    ]

    assert main(args) == 3
    warning = json.loads(capsys.readouterr().out)
    assert warning["requires_confirmation"] is True
    assert warning["secret_scan"]["finding_count"] >= 1
    assert token not in repr(warning)
    assert not package.exists()

    assert main(args + ["--allow-potential-secrets"]) == 0
    exported = json.loads(capsys.readouterr().out)
    assert exported["exported"] is True
    assert package.is_file()


def test_workspace_backup_and_restore_cli(tmp_path: Path, capsys) -> None:
    database = tmp_path / "cli-backup-source.sqlite3"
    assert main(["workspace", "init", "--database", str(database)]) == 0
    capsys.readouterr()
    assert main([
        "project", "create", "--database", str(database), "--name", "Backup CLI",
        "--summary", "Snapshot test",
    ]) == 0
    project = json.loads(capsys.readouterr().out)
    backup = tmp_path / "workspace.backup"

    assert main([
        "workspace", "backup", "--database", str(database),
        "--output", str(backup),
    ]) == 0
    backup_result = json.loads(capsys.readouterr().out)
    assert backup_result["backed_up"] is True

    restored_path = tmp_path / "restored.sqlite3"
    assert main([
        "workspace", "restore", "--backup", str(backup),
        "--database", str(restored_path),
    ]) == 0
    restored_result = json.loads(capsys.readouterr().out)
    assert restored_result["restored"] is True

    from yuktara_thread.application.workspace import WorkspaceService
    restored = WorkspaceService(restored_path)
    assert restored.projects.get(project["project_id"]).name == "Backup CLI"
