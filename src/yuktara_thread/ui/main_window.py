"""Main desktop workspace window and project screens."""
from __future__ import annotations

import json
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QInputDialog, QLabel, QListWidget, QListWidgetItem,
    QMainWindow, QMessageBox, QPushButton, QPlainTextEdit, QStackedWidget,
    QTabWidget, QVBoxLayout, QWidget,
)

from yuktara_thread.application.workspace import WorkspaceService


class ContextEditor(QWidget):
    def __init__(self, workspace: WorkspaceService, project_id: str, section) -> None:
        super().__init__()
        self.workspace = workspace
        self.project_id = project_id
        self.section_key = section.section_key
        self.revision = section.revision
        layout = QVBoxLayout(self)
        heading = QLabel(section.title)
        heading.setStyleSheet("font-weight: 600; font-size: 16px;")
        layout.addWidget(heading)
        self.editor = QPlainTextEdit(section.content)
        self.editor.setPlaceholderText("Capture the context another person will need...")
        layout.addWidget(self.editor, 1)
        save = QPushButton("Save changes")
        save.setObjectName("primary")
        save.clicked.connect(self.save)
        layout.addWidget(save, 0, Qt.AlignmentFlag.AlignRight)

    def save(self) -> None:
        try:
            section = self.workspace.save_context(
                self.project_id, self.section_key, self.editor.toPlainText(),
                expected_revision=self.revision,
            )
            self.revision = section.revision
            QMessageBox.information(self, "Saved", "Context revision saved.")
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not save", str(exc))


class EntityPanel(QWidget):
    """Compact list/create/rename/delete screen for one intelligence entity type."""

    def __init__(self, workspace: WorkspaceService, project_id: str, kind: str) -> None:
        super().__init__()
        self.workspace = workspace
        self.project_id = project_id
        self.kind = kind
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        description = QLabel(
            "Keep this information concise and useful to the next person continuing the project."
        )
        description.setObjectName("muted")
        layout.addWidget(description)
        layout.addWidget(self.list, 1)
        actions = QHBoxLayout()
        add = QPushButton(f"Add {kind}")
        rename = QPushButton("Rename")
        delete = QPushButton("Delete")
        add.setObjectName("primary")
        actions.addWidget(add)
        actions.addStretch(1)
        actions.addWidget(rename)
        actions.addWidget(delete)
        layout.addLayout(actions)
        add.clicked.connect(self.add_record)
        rename.clicked.connect(self.rename_record)
        delete.clicked.connect(self.delete_record)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for record in self.workspace.intelligence.list_records(self.project_id, self.kind):
            item = QListWidgetItem(str(record["title"]))
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.list.addItem(item)

    def add_record(self) -> None:
        title, accepted = QInputDialog.getText(self, f"New {self.kind}", "Title")
        if not accepted:
            return
        try:
            creators = {
                "decision": self.workspace.intelligence.create_decision,
                "task": self.workspace.intelligence.create_task,
                "milestone": self.workspace.intelligence.create_milestone,
                "reference": self.workspace.intelligence.create_reference,
            }
            creators[self.kind](self.project_id, title=title)
            self.refresh()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not add item", str(exc))

    def rename_record(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        id_key = f"{self.kind}_id"
        title, accepted = QInputDialog.getText(
            self, f"Rename {self.kind}", "Title", text=str(record["title"])
        )
        if not accepted:
            return
        try:
            self.workspace.intelligence.update_record(
                self.project_id, self.kind, str(record[id_key]), title=title
            )
            self.refresh()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not rename item", str(exc))

    def delete_record(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        answer = QMessageBox.question(
            self, "Delete item", f"Delete '{record['title']}'? This action is recorded in project history."
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.workspace.intelligence.delete_record(
                self.project_id, self.kind, str(record[f"{self.kind}_id"])
            )
            self.refresh()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not delete item", str(exc))


class ProjectPage(QWidget):
    def __init__(self, workspace: WorkspaceService, project) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel(project.name)
        title.setObjectName("pageTitle")
        summary = QLabel(project.summary or "No project summary yet.")
        summary.setObjectName("muted")
        summary.setWordWrap(True)
        layout.addWidget(title)
        layout.addWidget(summary)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.addWidget(QLabel("Project workspace"))
        overview_layout.addWidget(QLabel(
            "Use the tabs to preserve decisions, execution work, milestones, references and context."
        ))
        overview_layout.addStretch(1)
        tabs.addTab(overview, "Overview")

        context_tabs = QTabWidget()
        for section in workspace.get_context(project.project_id):
            context_tabs.addTab(ContextEditor(workspace, project.project_id, section), section.title)
        tabs.addTab(context_tabs, "Context")

        for kind, label in (
            ("decision", "Decisions"), ("task", "Tasks"),
            ("milestone", "Milestones"), ("reference", "References"),
        ):
            tabs.addTab(EntityPanel(workspace, project.project_id, kind), label)

        activity = QWidget()
        activity_layout = QVBoxLayout(activity)
        events = QListWidget()
        for event in workspace.intelligence.timeline(project.project_id, limit=250):
            payload = json.dumps(event["payload"], ensure_ascii=False, sort_keys=True)
            events.addItem(f"{event['created_at']}  ·  {event['event_type']}  ·  {payload}")
        activity_layout.addWidget(events)
        tabs.addTab(activity, "Activity")


class MainWindow(QMainWindow):
    def __init__(self, database_path: Path) -> None:
        super().__init__()
        self.workspace = WorkspaceService(database_path)
        self.setWindowTitle("Yuktara Thread")
        self.setMinimumSize(980, 680)
        self.resize(1240, 820)

        root = QWidget()
        root.setObjectName("root")
        root_layout = QHBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(250)
        side_layout = QVBoxLayout(sidebar)
        side_layout.setContentsMargins(16, 18, 16, 16)
        brand = QLabel("Yuktara Thread")
        brand.setObjectName("brand")
        side_layout.addWidget(brand)
        side_layout.addWidget(QLabel("WORKSPACE"))
        self.projects = QListWidget()
        side_layout.addWidget(self.projects, 1)
        create = QPushButton("＋  New project")
        create.setObjectName("primary")
        side_layout.addWidget(create)
        side_layout.addWidget(QLabel(f"Database: {database_path.name}"))

        self.pages = QStackedWidget()
        self.empty = QWidget()
        empty_layout = QVBoxLayout(self.empty)
        empty_layout.addStretch(1)
        empty_title = QLabel("Choose a project")
        empty_title.setObjectName("pageTitle")
        empty_title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_hint = QLabel("Create a workspace project or select one from the sidebar.")
        empty_hint.setObjectName("muted")
        empty_hint.setAlignment(Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_title)
        empty_layout.addWidget(empty_hint)
        empty_layout.addStretch(1)
        self.pages.addWidget(self.empty)

        root_layout.addWidget(sidebar)
        root_layout.addWidget(self.pages, 1)
        self.setCentralWidget(root)

        create.clicked.connect(self.create_project)
        self.projects.currentItemChanged.connect(self.select_project)
        self.refresh_projects()

    def refresh_projects(self, selected_id: str | None = None) -> None:
        self.projects.clear()
        projects = self.workspace.list_projects()
        for project in projects:
            item = QListWidgetItem(project.name)
            item.setData(Qt.ItemDataRole.UserRole, project.project_id)
            self.projects.addItem(item)
            if project.project_id == selected_id:
                self.projects.setCurrentItem(item)
        if not projects:
            self.pages.setCurrentWidget(self.empty)

    def create_project(self) -> None:
        name, accepted = QInputDialog.getText(self, "New project", "Project name")
        if not accepted:
            return
        summary, summary_accepted = QInputDialog.getText(self, "Project summary", "Short summary (optional)")
        if not summary_accepted:
            summary = ""
        try:
            project = self.workspace.create_project(name, summary)
            self.refresh_projects(project.project_id)
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not create project", str(exc))

    def select_project(self, current, _previous) -> None:
        if current is None:
            return
        project_id = current.data(Qt.ItemDataRole.UserRole)
        project = self.workspace.projects.get(project_id)
        if project is None:
            QMessageBox.warning(self, "Project unavailable", "This project could not be found.")
            self.refresh_projects()
            return
        page = ProjectPage(self.workspace, project)
        self.pages.addWidget(page)
        self.pages.setCurrentWidget(page)
