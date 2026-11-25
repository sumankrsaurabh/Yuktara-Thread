"""Offscreen Qt smoke tests for the optional desktop application."""
from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QMessageBox, QPlainTextEdit, QTabWidget

from yuktara_thread.ui.main_window import EntityEditorDialog, EntityPanel, MainWindow


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


def test_decision_editor_preserves_structured_fields(application):
    dialog = EntityEditorDialog("decision")
    dialog.fields["title"].setText("Use SQLite")
    dialog.fields["problem"].setPlainText("Where should local data live?")
    dialog.fields["alternatives"].setPlainText("JSON files" + chr(10) + "SQLite")
    dialog.fields["rationale"].setPlainText("Transactional updates and queries.")

    values = dialog.values()

    assert values["title"] == "Use SQLite"
    assert values["problem"] == "Where should local data live?"
    assert values["alternatives"] == ["JSON files", "SQLite"]
    assert values["status"] == "proposed"
    dialog.close()


def test_task_dependency_controls_use_audited_service(tmp_path, application):
    window = MainWindow(tmp_path / "dependency-smoke.sqlite3")
    project = window.workspace.create_project("Dependency project")
    prerequisite = window.workspace.intelligence.create_task(
        project.project_id, title="Design schema"
    )
    dependent = window.workspace.intelligence.create_task(
        project.project_id, title="Implement repository"
    )
    window.refresh_projects(project.project_id)
    application.processEvents()

    tabs = window.project_page.findChild(QTabWidget)
    panel = tabs.widget(3)
    assert isinstance(panel, EntityPanel)
    panel.refresh()
    panel.list.setCurrentRow(0)
    application.processEvents()

    # Select the dependent task by its record ID, not by assumed sort order.
    for index in range(panel.list.count()):
        item = panel.list.item(index)
        if item.data(Qt.ItemDataRole.UserRole)["task_id"] == dependent["task_id"]:
            panel.list.setCurrentItem(item)
            break

    picker_index = panel.prerequisite_picker.findData(prerequisite["task_id"])
    assert picker_index >= 0
    panel.prerequisite_picker.setCurrentIndex(picker_index)
    panel.add_dependency()
    assert prerequisite["task_id"] in window.workspace.intelligence.list_task_dependencies(
        dependent["task_id"]
    )
    assert panel.dependency_list.count() == 1

    panel.remove_dependency()
    assert window.workspace.intelligence.list_task_dependencies(dependent["task_id"]) == []
    window.close()
    application.processEvents()


def test_archive_control_archives_project_and_removes_it_from_active_list(
    tmp_path, application, monkeypatch
):
    window = MainWindow(tmp_path / "archive-smoke.sqlite3")
    project = window.workspace.create_project("Archive me")
    window.refresh_projects(project.project_id)
    monkeypatch.setattr(
        QMessageBox, "question",
        lambda *_args, **_kwargs: QMessageBox.StandardButton.Yes,
    )

    window.archive_project(project)

    assert window.workspace.list_projects() == []
    assert window.workspace.list_projects(include_archived=True)[0].status == "archived"
    window.close()
    application.processEvents()
