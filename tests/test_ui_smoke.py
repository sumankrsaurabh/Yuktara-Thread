"""Offscreen Qt smoke tests for the optional desktop application."""
from __future__ import annotations

import pytest

PySide6 = pytest.importorskip("PySide6")

from PySide6.QtCore import QCoreApplication, QEvent, Qt
from PySide6.QtWidgets import QApplication, QFileDialog, QInputDialog, QLabel, QMessageBox, QTabWidget

from yuktara_thread.domain.models import ProjectContext
from yuktara_thread.infrastructure.package import create_package, preview_package
from yuktara_thread.ui.main_window import (
    ActivityPanel, EntityEditorDialog, EntityPanel, MainWindow, PackagePreviewDialog,
)


@pytest.fixture(scope="module")
def application():
    app = QApplication.instance() or QApplication([])
    yield app


def dispose_widget(widget, application):
    widget.close()
    widget.deleteLater()
    QCoreApplication.sendPostedEvents(None, QEvent.Type.DeferredDelete)
    application.processEvents()


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

    dispose_widget(window, application)


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
    dispose_widget(dialog, application)


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
    panel.dependency_list.setCurrentRow(0)

    panel.remove_dependency()
    assert window.workspace.intelligence.list_task_dependencies(dependent["task_id"]) == []
    dispose_widget(window, application)


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
    assert window.pages.count() == 1
    dispose_widget(window, application)


def test_activity_panel_filters_by_event_type_and_text(tmp_path, application):
    window = MainWindow(tmp_path / "activity-smoke.sqlite3")
    project = window.workspace.create_project("Activity project")
    window.workspace.intelligence.create_task(project.project_id, title="Write migration")
    panel = ActivityPanel(window.workspace, project.project_id)

    assert panel.list.count() >= 2
    panel.search.setText("Write migration")
    assert panel.list.count() == 1
    panel.search.clear()
    task_event_index = panel.kind_filter.findData("task.created")
    assert task_event_index >= 0
    panel.kind_filter.setCurrentIndex(task_event_index)
    assert panel.list.count() == 1
    assert "Task added" in panel.list.item(0).text()

    dispose_widget(panel, application)
    dispose_widget(window, application)


def test_package_preview_dialog_displays_verified_file_list(tmp_path, application):
    source = tmp_path / "package-source"
    source.mkdir()
    (source / "handover.md").write_text("Next steps", encoding="utf-8")
    package = tmp_path / "preview.thread"
    create_package(source, package, ProjectContext.create("Preview in UI").to_dict())

    preview = preview_package(package)
    dialog = PackagePreviewDialog(package, preview)

    assert "Preview in UI" in dialog.findChild(QLabel).text()
    assert "handover.md" in dialog.file_list.toPlainText()
    assert "Integrity checks passed" in dialog.findChildren(QLabel)[1].text()
    dispose_widget(dialog, application)


def test_package_preview_saves_handover_report(tmp_path, application, monkeypatch):
    source = tmp_path / "report-source"
    source.mkdir()
    (source / "README.md").write_text("Project instructions", encoding="utf-8")
    package = tmp_path / "report.thread"
    create_package(source, package, ProjectContext.create("Report project", "A test report").to_dict())
    dialog = PackagePreviewDialog(package, preview_package(package))
    output = tmp_path / "handover.md"

    monkeypatch.setattr(QFileDialog, "getSaveFileName", lambda *_args, **_kwargs: (str(output), "Markdown"))
    monkeypatch.setattr(QMessageBox, "information", lambda *_args, **_kwargs: QMessageBox.StandardButton.Ok)

    dialog.save_report()

    report = output.read_text(encoding="utf-8")
    assert "# Handover: Report project" in report
    assert "`README.md`" in report
    dispose_widget(dialog, application)


def test_package_preview_imports_project_into_workspace(tmp_path, application, monkeypatch):
    from yuktara_thread.application.workspace import WorkspaceService

    source = tmp_path / "workspace-import-source"
    source.mkdir()
    (source / "README.md").write_text("Workspace handover", encoding="utf-8")
    package = tmp_path / "workspace-import.thread"
    create_package(source, package, ProjectContext.create("Imported through UI").to_dict())
    workspace = WorkspaceService(tmp_path / "ui-import.sqlite3")
    destination_parent = tmp_path / "received"
    destination_parent.mkdir()
    monkeypatch.setattr(QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(destination_parent))
    monkeypatch.setattr(QInputDialog, "getText", lambda *_args, **_kwargs: ("ui-import", True))
    monkeypatch.setattr(QMessageBox, "information", lambda *_args, **_kwargs: QMessageBox.StandardButton.Ok)
    selected = []
    dialog = PackagePreviewDialog(
        package, preview_package(package), workspace=workspace,
        on_import=selected.append,
    )

    dialog.import_to_workspace()

    projects = workspace.list_projects()
    assert len(projects) == 1
    assert projects[0].name == "Imported through UI"
    assert selected == [projects[0].project_id]
    assert (destination_parent / "ui-import" / "files" / "README.md").read_text(encoding="utf-8") == "Workspace handover"
    dispose_widget(dialog, application)
