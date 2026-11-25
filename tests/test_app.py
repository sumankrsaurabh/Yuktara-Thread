from pathlib import Path

from yuktara_thread.ui import app


def test_desktop_launcher_can_prompt_for_workspace(monkeypatch) -> None:
    received = []
    monkeypatch.setattr(app, "run", lambda database_path=None: received.append(database_path) or 7)

    assert app.main([]) == 7
    assert received == [None]


def test_desktop_launcher_passes_explicit_database(monkeypatch, tmp_path: Path) -> None:
    database = tmp_path / "chosen.sqlite3"
    received = []
    monkeypatch.setattr(app, "run", lambda database_path=None: received.append(database_path) or 0)

    assert app.main(["--database", str(database)]) == 0
    assert received == [database]
