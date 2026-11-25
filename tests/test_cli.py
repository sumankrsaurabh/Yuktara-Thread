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
