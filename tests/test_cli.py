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
