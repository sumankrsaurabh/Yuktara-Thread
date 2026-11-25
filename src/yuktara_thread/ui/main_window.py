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


class EntityEditorDialog(QDialog):
    """Typed editor for the structured fields of a project intelligence record."""

    FIELD_SPECS = {
        "decision": [
            ("title", "Title", "line", []),
            ("problem", "Problem", "area", []),
            ("selected_option", "Selected option", "line", []),
            ("alternatives", "Alternatives (one per line)", "area", []),
            ("rationale", "Rationale", "area", []),
            ("consequences", "Consequences", "area", []),
            ("status", "Status", "choice", ["proposed", "accepted", "rejected", "superseded"]),
        ],
        "task": [
            ("title", "Title", "line", []),
            ("description", "Description", "area", []),
            ("status", "Status", "choice", ["open", "in_progress", "blocked", "completed", "cancelled"]),
            ("priority", "Priority", "choice", ["low", "normal", "high", "critical"]),
            ("owner", "Owner", "line", []),
            ("due_at", "Due date (ISO 8601)", "line", []),
        ],
        "milestone": [
            ("title", "Title", "line", []),
            ("description", "Description", "area", []),
            ("due_at", "Due date (ISO 8601)", "line", []),
            ("status", "Status", "choice", ["planned", "in_progress", "completed", "cancelled"]),
        ],
        "reference": [
            ("title", "Title", "line", []),
            ("reference_type", "Type", "choice", ["document", "repository", "website", "issue", "person", "other"]),
            ("uri", "URI or location", "line", []),
            ("notes", "Notes", "area", []),
        ],
    }

    def __init__(self, kind: str, values: dict | None = None, parent=None) -> None:
        super().__init__(parent)
        self.kind = kind
        self.fields = {}
        self.setWindowTitle(f"{'Edit' if values else 'New'} {kind}")
        self.setMinimumWidth(460)
        form = QFormLayout(self)
        initial = values or {}
        for key, label, widget_type, choices in self.FIELD_SPECS[kind]:
            if widget_type == "area":
                widget = QPlainTextEdit()
                widget.setPlainText(
                    "\\n".join(initial.get(key, [])) if key == "alternatives"
                    else str(initial.get(key) or "")
                )
                widget.setMinimumHeight(72)
            elif widget_type == "choice":
                widget = QComboBox()
                widget.addItems(choices)
                widget.setCurrentText(str(initial.get(key) or choices[0]))
            else:
                widget = QLineEdit(str(initial.get(key) or ""))
            self.fields[key] = widget
            form.addRow(label, widget)

        buttons = QHBoxLayout()
        buttons.addStretch(1)
        cancel = QPushButton("Cancel")
        save = QPushButton("Save")
        save.setObjectName("primary")
        cancel.clicked.connect(self.reject)
        save.clicked.connect(self.accept)
        buttons.addWidget(cancel)
        buttons.addWidget(save)
        form.addRow(buttons)

    def values(self) -> dict:
        result = {}
        for key, widget in self.fields.items():
            if isinstance(widget, QPlainTextEdit):
                value = widget.toPlainText().strip()
                if key == "alternatives":
                    result[key] = [line.strip() for line in value.splitlines() if line.strip()]
                    continue
            elif isinstance(widget, QComboBox):
                value = widget.currentText()
            else:
                value = widget.text().strip()
            result[key] = value or (None if key == "due_at" else "")
        return result


class EntityPanel(QWidget):
    """Full-field CRUD editor for decisions, tasks, milestones and references."""

    def __init__(self, workspace: WorkspaceService, project_id: str, kind: str) -> None:
        super().__init__()
        self.workspace = workspace
        self.project_id = project_id
        self.kind = kind
        self.list = QListWidget()
        layout = QVBoxLayout(self)
        description = QLabel(
            "Capture enough detail for another person to understand and continue this work."
        )
        description.setObjectName("muted")
        layout.addWidget(description)
        layout.addWidget(self.list, 1)
        actions = QHBoxLayout()
        add = QPushButton(f"Add {kind}")
        edit = QPushButton("Edit details")
        delete = QPushButton("Delete")
        add.setObjectName("primary")
        actions.addWidget(add)
        actions.addStretch(1)
        actions.addWidget(edit)
        actions.addWidget(delete)
        layout.addLayout(actions)
        add.clicked.connect(self.add_record)
        edit.clicked.connect(self.edit_record)
        delete.clicked.connect(self.delete_record)
        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for record in self.workspace.intelligence.list_records(self.project_id, self.kind):
            item = QListWidgetItem(str(record["title"]))
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.list.addItem(item)

    def add_record(self) -> None:
        dialog = EntityEditorDialog(self.kind, parent=self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            creators = {
                "decision": self.workspace.intelligence.create_decision,
                "task": self.workspace.intelligence.create_task,
                "milestone": self.workspace.intelligence.create_milestone,
                "reference": self.workspace.intelligence.create_reference,
            }
            creators[self.kind](self.project_id, **dialog.values())
            self.refresh()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not add item", str(exc))

    def edit_record(self) -> None:
        item = self.list.currentItem()
        if item is None:
            return
        record = item.data(Qt.ItemDataRole.UserRole)
        dialog = EntityEditorDialog(self.kind, record, self)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            self.workspace.intelligence.update_record(
                self.project_id, self.kind, str(record[f"{self.kind}_id"]),
                **dialog.values(),
            )
            self.refresh()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update item", str(exc))

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
        self.project_page = None
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
        if self.project_page is not None:
            self.pages.removeWidget(self.project_page)
            self.project_page.deleteLater()
        self.project_page = ProjectPage(self.workspace, project)
        self.pages.addWidget(self.project_page)
        self.pages.setCurrentWidget(self.project_page)
