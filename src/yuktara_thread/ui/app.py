"""Desktop application bootstrap; PySide6 is an optional dependency."""
from __future__ import annotations

import argparse
import sqlite3
from pathlib import Path
import sys


def run(database_path: Path | None = None) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise RuntimeError(
            "The desktop interface requires PySide6. Install it with: "
            "python -m pip install -e '.[desktop]'"
        ) from exc

    from PySide6.QtWidgets import QFileDialog, QMessageBox
    from yuktara_thread.ui.main_window import MainWindow
    from yuktara_thread.ui.styles import APP_STYLE

    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName("Yuktara Thread")
    application.setOrganizationName("Yuktara Technologies")
    application.setStyleSheet(APP_STYLE)

    if database_path is None:
        choice = QMessageBox.question(
            None, "Yuktara Thread workspace",
            "Open an existing workspace? Choose No to create a new workspace database.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Yes,
        )
        if choice == QMessageBox.StandardButton.Cancel:
            return 0
        if choice == QMessageBox.StandardButton.Yes:
            filename, _filter = QFileDialog.getOpenFileName(
                None, "Open workspace database", "",
                "SQLite databases (*.sqlite3 *.db);;All files (*)",
            )
        else:
            filename, _filter = QFileDialog.getSaveFileName(
                None, "Create workspace database", "yuktara-thread.sqlite3",
                "SQLite databases (*.sqlite3);;All files (*)",
            )
            if filename and Path(filename).exists():
                QMessageBox.warning(
                    None, "Database already exists",
                    "Choose a new filename or open the existing database instead.",
                )
                return 2
        if not filename:
            return 0
        database_path = Path(filename)

    try:
        window = MainWindow(database_path)
    except (OSError, RuntimeError, ValueError, sqlite3.Error) as exc:
        QMessageBox.critical(None, "Could not open workspace", str(exc))
        return 2
    window.show()
    return application.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thread-desktop")
    parser.add_argument("--database", required=False, type=Path,
                        help="Path to the local SQLite workspace database")
    args = parser.parse_args(argv)
    try:
        return run(args.database)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
