"""Offscreen Qt smoke tests for the optional desktop application."""
from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtWidgets import QApplication, QTabWidget

from yuktara_thread.ui.main_window import MainWindow


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    yield app


def test_main_window_loads_and_opens_project(tmp_path, application):
    database = tmp_path / "desktop-smoke.sqlite3"
    window = MainWindow(database)

    project = window.workspace.create_project(
        "Desktop smoke project", "Created by the offscreen UI test."
    )
    window.refresh_projects(project.project_id)
    application.processEvents()

    assert window.windowTitle() == "Yuktara Thread"
    assert window.projects.count() == 1
    assert window.project_page is not None
    tabs = window.project_page.findChild(QTabWidget)
    assert tabs is not None
    assert [tabs.tabText(i) for i in range(tabs.count())] == [
        "Overview", "Context", "Decisions", "Tasks",
        "Milestones", "References", "Activity",
    ]

    window.close()
    application.processEvents()
