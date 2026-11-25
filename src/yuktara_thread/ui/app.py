"""Desktop application bootstrap; PySide6 is an optional dependency."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys


def run(database_path: Path) -> int:
    try:
        from PySide6.QtWidgets import QApplication
    except ImportError as exc:
        raise RuntimeError(
            "The desktop interface requires PySide6. Install it with: "
            "python -m pip install -e '.[desktop]'"
        ) from exc

    from yuktara_thread.ui.main_window import MainWindow
    from yuktara_thread.ui.styles import APP_STYLE

    application = QApplication.instance() or QApplication(sys.argv[:1])
    application.setApplicationName("Yuktara Thread")
    application.setOrganizationName("Yuktara Technologies")
    application.setStyleSheet(APP_STYLE)
    window = MainWindow(database_path)
    window.show()
    return application.exec()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="thread-desktop")
    parser.add_argument("--database", required=True, type=Path,
                        help="Path to the local SQLite workspace database")
    args = parser.parse_args(argv)
    try:
        return run(args.database)
    except (OSError, RuntimeError, ValueError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
