"""Main desktop workspace window and project screens."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog,
    QFileDialog, QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QStackedWidget, QTabWidget, QVBoxLayout, QWidget,
)

from yuktara_thread.application.backup import backup_workspace, restore_workspace
from yuktara_thread.application.handover import export_workspace_project, import_workspace_project
from yuktara_thread.application.handover_report import render_handover_report
from yuktara_thread.application.readiness import assess_handover_readiness
from yuktara_thread.application.secret_scan import scan_selected_files
from yuktara_thread.application.search import search_workspace
from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.infrastructure.package import PackageError, import_package, preview_package


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
                    "\n".join(initial.get(key, [])) if key == "alternatives"
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

        self.dependency_list = None
        self.prerequisite_picker = None
        if self.kind == "task":
            dependency_heading = QLabel("Task prerequisites")
            dependency_heading.setStyleSheet("font-weight: 600;")
            layout.addWidget(dependency_heading)
            dependency_row = QHBoxLayout()
            self.prerequisite_picker = QComboBox()
            self.prerequisite_picker.setPlaceholderText("Select a prerequisite task")
            add_dependency = QPushButton("Add prerequisite")
            remove_dependency = QPushButton("Remove selected")
            dependency_row.addWidget(self.prerequisite_picker, 1)
            dependency_row.addWidget(add_dependency)
            dependency_row.addWidget(remove_dependency)
            layout.addLayout(dependency_row)
            self.dependency_list = QListWidget()
            self.dependency_list.setMaximumHeight(120)
            layout.addWidget(self.dependency_list)
            add_dependency.clicked.connect(self.add_dependency)
            remove_dependency.clicked.connect(self.remove_dependency)
            self.list.currentItemChanged.connect(self.refresh_dependencies)

        self.refresh()

    def refresh(self) -> None:
        self.list.clear()
        for record in self.workspace.intelligence.list_records(self.project_id, self.kind):
            item = QListWidgetItem(str(record["title"]))
            item.setData(Qt.ItemDataRole.UserRole, record)
            self.list.addItem(item)

    def refresh_dependencies(self, *_args) -> None:
        if self.kind != "task" or self.dependency_list is None:
            return
        self.dependency_list.clear()
        self.prerequisite_picker.clear()
        tasks = self.workspace.intelligence.list_records(self.project_id, "task")
        current = self.list.currentItem()
        if current is None:
            return
        selected = current.data(Qt.ItemDataRole.UserRole)
        task_id = str(selected["task_id"])
        for task in tasks:
            if str(task["task_id"]) != task_id:
                self.prerequisite_picker.addItem(str(task["title"]), str(task["task_id"]))
        by_id = {str(task["task_id"]): str(task["title"]) for task in tasks}
        for dependency_id in self.workspace.intelligence.list_task_dependencies(task_id):
            title = by_id.get(dependency_id, "Missing task")
            item = QListWidgetItem(title)
            item.setData(Qt.ItemDataRole.UserRole, dependency_id)
            self.dependency_list.addItem(item)

    def add_dependency(self) -> None:
        current = self.list.currentItem()
        if current is None or self.prerequisite_picker.count() == 0:
            return
        task = current.data(Qt.ItemDataRole.UserRole)
        prerequisite_id = self.prerequisite_picker.currentData()
        try:
            self.workspace.intelligence.add_task_dependency(
                self.project_id, str(task["task_id"]), str(prerequisite_id)
            )
            self.refresh_dependencies()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not add prerequisite", str(exc))

    def remove_dependency(self) -> None:
        current_task = self.list.currentItem()
        selected_dependency = self.dependency_list.currentItem() if self.dependency_list else None
        if current_task is None or selected_dependency is None:
            return
        task = current_task.data(Qt.ItemDataRole.UserRole)
        try:
            self.workspace.intelligence.remove_task_dependency(
                self.project_id, str(task["task_id"]),
                str(selected_dependency.data(Qt.ItemDataRole.UserRole)),
            )
            self.refresh_dependencies()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not remove prerequisite", str(exc))

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


class ActivityPanel(QWidget):
    """Readable, searchable and type-filterable project activity stream."""

    LABELS = {
        "project.created": "Project created",
        "project.updated": "Project details updated",
        "project.archived": "Project archived",
        "context.updated": "Context updated",
        "decision.created": "Decision added",
        "decision.updated": "Decision updated",
        "decision.deleted": "Decision deleted",
        "task.created": "Task added",
        "task.updated": "Task updated",
        "task.deleted": "Task deleted",
        "task.dependency_added": "Task prerequisite added",
        "task.dependency_removed": "Task prerequisite removed",
        "milestone.created": "Milestone added",
        "milestone.updated": "Milestone updated",
        "milestone.deleted": "Milestone deleted",
        "reference.created": "Reference added",
        "reference.updated": "Reference updated",
        "reference.deleted": "Reference deleted",
    }

    def __init__(self, workspace: WorkspaceService, project_id: str) -> None:
        super().__init__()
        self.workspace = workspace
        self.project_id = project_id
        self.events = workspace.intelligence.timeline(project_id, limit=500)

        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search activity...")
        self.kind_filter = QComboBox()
        self.kind_filter.addItem("All activity", "")
        event_types = sorted({str(event["event_type"]) for event in self.events})
        for event_type in event_types:
            self.kind_filter.addItem(self.LABELS.get(event_type, event_type), event_type)
        filters.addWidget(self.search, 1)
        filters.addWidget(self.kind_filter)
        layout.addLayout(filters)

        self.list = QListWidget()
        layout.addWidget(self.list, 1)
        self.search.textChanged.connect(self.apply_filters)
        self.kind_filter.currentIndexChanged.connect(self.apply_filters)
        self.apply_filters()

    def _description(self, event: dict) -> str:
        payload = event.get("payload") or {}
        if "title" in payload:
            return str(payload["title"])
        if "section_key" in payload:
            return f"Section: {payload['section_key']}"
        if "depends_on_task_id" in payload:
            return "A task prerequisite relationship changed"
        if "changed_fields" in payload:
            return "Updated: " + ", ".join(payload["changed_fields"])
        if payload.get("summary_changed"):
            return "Project summary changed"
        return ""

    def apply_filters(self, *_args) -> None:
        query = self.search.text().strip().casefold()
        selected_type = self.kind_filter.currentData()
        self.list.clear()
        for event in self.events:
            event_type = str(event["event_type"])
            label = self.LABELS.get(event_type, event_type.replace(".", " ").title())
            detail = self._description(event)
            timestamp = str(event["created_at"])
            searchable = f"{label} {detail} {timestamp}".casefold()
            if selected_type and event_type != selected_type:
                continue
            if query and query not in searchable:
                continue
            item = QListWidgetItem(f"{label}  ·  {timestamp}\n{detail}".rstrip())
            item.setData(Qt.ItemDataRole.UserRole, event)
            self.list.addItem(item)


class ReadinessPanel(QWidget):
    """Live, deterministic handover completeness checks for a workspace project."""

    def __init__(self, workspace: WorkspaceService, project) -> None:
        super().__init__()
        self.workspace = workspace
        self.project = project
        layout = QVBoxLayout(self)
        heading = QLabel("Handover readiness")
        heading.setStyleSheet("font-weight: 600;")
        layout.addWidget(heading)
        self.summary = QLabel()
        self.summary.setWordWrap(True)
        layout.addWidget(self.summary)
        self.checks = QListWidget()
        self.checks.setMaximumHeight(230)
        layout.addWidget(self.checks)
        refresh = QPushButton("Refresh readiness checks")
        refresh.clicked.connect(self.refresh)
        layout.addWidget(refresh, 0, Qt.AlignmentFlag.AlignLeft)
        self.refresh()

    def refresh(self) -> None:
        context = self.workspace.get_context(self.project.project_id)
        records = {
            kind: self.workspace.intelligence.list_records(self.project.project_id, kind)
            for kind in ("decision", "task", "milestone", "reference")
        }
        result = assess_handover_readiness(
            self.project, context, records["decision"], records["task"],
            records["milestone"], records["reference"],
        )
        status = result["status"].replace("_", " ").title()
        self.summary.setText(
            f"{result['score']}% completeness indicator · {status}\n"
            "This checks documentation completeness, not correctness or safety."
        )
        self.checks.clear()
        for check in result["checks"]:
            symbol = "✓" if check["passed"] else "○"
            priority = "Required" if check["required"] else "Recommended"
            item = QListWidgetItem(
                f"{symbol}  {check['label']} · {priority}"
                + ("" if check["passed"] else f" — {check['detail']}")
            )
            self.checks.addItem(item)


class ProjectPage(QWidget):
    def __init__(self, workspace: WorkspaceService, project, *,
                 on_edit=None, on_archive=None) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        title = QLabel(project.name)
        title.setObjectName("pageTitle")
        summary = QLabel(project.summary or "No project summary yet.")
        summary.setObjectName("muted")
        summary.setWordWrap(True)
        header = QHBoxLayout()
        header.addWidget(title, 1)
        self.edit_project = QPushButton("Edit project")
        self.archive_project = QPushButton("Archive project")
        header.addWidget(self.edit_project)
        header.addWidget(self.archive_project)
        layout.addLayout(header)
        layout.addWidget(summary)
        self.edit_project.clicked.connect(lambda: on_edit(project) if on_edit else None)
        self.archive_project.clicked.connect(lambda: on_archive(project) if on_archive else None)
        tabs = QTabWidget()
        layout.addWidget(tabs, 1)

        overview = QWidget()
        overview_layout = QVBoxLayout(overview)
        overview_layout.addWidget(QLabel("Project workspace"))
        overview_layout.addWidget(QLabel(
            "Use the tabs to preserve decisions, execution work, milestones, references and context."
        ))
        overview_layout.addWidget(ReadinessPanel(workspace, project))
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

        tabs.addTab(ActivityPanel(workspace, project.project_id), "Activity")


class SearchDialog(QDialog):
    """Search local project content and open the owning project."""

    def __init__(self, workspace: WorkspaceService, on_open=None, parent=None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.on_open = on_open
        self.setWindowTitle("Search workspace")
        self.setMinimumSize(640, 480)
        layout = QVBoxLayout(self)
        row = QHBoxLayout()
        self.query = QLineEdit()
        self.query.setPlaceholderText("Search projects, context, decisions, tasks…")
        self.query.returnPressed.connect(self.run_search)
        search_button = QPushButton("Search")
        search_button.setObjectName("primary")
        search_button.clicked.connect(self.run_search)
        row.addWidget(self.query, 1)
        row.addWidget(search_button)
        layout.addLayout(row)
        self.results = QListWidget()
        self.results.itemDoubleClicked.connect(lambda _item: self.open_selected())
        layout.addWidget(self.results, 1)
        self.status = QLabel("Search is local to this workspace. Enter at least two characters.")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        open_button = QPushButton("Open project")
        open_button.clicked.connect(self.open_selected)
        layout.addWidget(open_button, 0, Qt.AlignmentFlag.AlignRight)

    def run_search(self) -> None:
        try:
            matches = search_workspace(self.workspace, self.query.text())
        except ValueError as exc:
            self.status.setText(str(exc))
            self.results.clear()
            return
        self.results.clear()
        for result in matches:
            item = QListWidgetItem(
                f"{result['project_name']}  ·  {result['entity_type'].title()}\n"
                f"{result['title']}\n{result['excerpt'] or ''}"
            )
            item.setData(Qt.ItemDataRole.UserRole, result)
            self.results.addItem(item)
        self.status.setText(
            f"{len(matches)} result(s). Double-click a result to open its project."
        )

    def open_selected(self) -> None:
        item = self.results.currentItem()
        if item is None:
            return
        result = item.data(Qt.ItemDataRole.UserRole)
        if self.on_open is not None:
            self.on_open(str(result["project_id"]))
        self.accept()


class PackagePreviewDialog(QDialog):
    """Verified package preview with an explicit, staged file-extraction action."""

    def __init__(
        self, package_path: Path, preview: dict, parent=None, *,
        workspace: WorkspaceService | None = None, on_import=None,
    ) -> None:
        super().__init__(parent)
        self.package_path = package_path
        self.preview = preview
        self.workspace = workspace
        self.on_import = on_import
        self.setWindowTitle("Thread package preview")
        self.setMinimumSize(620, 520)

        layout = QVBoxLayout(self)
        project = preview["project"]
        name = str(project.get("name") or "Unnamed project")
        summary = str(project.get("summary") or "No summary provided")
        total_bytes = sum(int(item["size"]) for item in preview["files"])
        decisions = len(project.get("decisions")) if isinstance(project.get("decisions"), list) else 0
        tasks = len(project.get("tasks")) if isinstance(project.get("tasks"), list) else 0
        milestones = len(project.get("milestones")) if isinstance(project.get("milestones"), list) else 0
        references = len(project.get("references")) if isinstance(project.get("references"), list) else 0
        context_sections = len(project.get("context_sections")) if isinstance(project.get("context_sections"), list) else 0
        readiness = project.get("handover_readiness")
        readiness_line = (
            f"Readiness: {readiness.get('score')}% · "
            f"{str(readiness.get('status', 'unknown')).replace('_', ' ')}"
            if isinstance(readiness, dict) and isinstance(readiness.get("score"), int)
            else "Readiness: not calculated"
        )
        overview = QLabel(
            f"{name}\n{summary}\n\n"
            f"{preview['file_count']} files · {total_bytes:,} bytes · "
            f"{context_sections} context sections · {decisions} decisions · "
            f"{tasks} tasks · {milestones} milestones · {references} references\n"
            f"{readiness_line}\nFormat {preview['format_version']}"
        )
        overview.setTextFormat(Qt.TextFormat.PlainText)
        overview.setWordWrap(True)
        layout.addWidget(overview)

        self.file_list = QPlainTextEdit()
        self.file_list.setReadOnly(True)
        self.file_list.setPlainText(
            "\n".join(
                f"{item['path']}  ·  {item['size']:,} bytes"
                for item in preview["files"]
            ) or "This package contains no files."
        )
        layout.addWidget(self.file_list, 1)

        notice = QLabel(
            "Integrity checks passed. Previewing does not extract files. "
            "Package verification does not establish who created or signed it."
        )
        notice.setWordWrap(True)
        notice.setObjectName("muted")
        layout.addWidget(notice)

        actions = QHBoxLayout()
        actions.addStretch(1)
        close = QPushButton("Close")
        report = QPushButton("Save handover report…")
        extract = QPushButton("Extract files…")
        extract.setObjectName("primary")
        close.clicked.connect(self.reject)
        report.clicked.connect(self.save_report)
        extract.clicked.connect(self.extract_files)
        actions.addWidget(close)
        actions.addWidget(report)
        actions.addWidget(extract)
        if self.workspace is not None:
            import_project = QPushButton("Import project…")
            import_project.setObjectName("primary")
            import_project.clicked.connect(self.import_to_workspace)
            actions.addWidget(import_project)
        layout.addLayout(actions)

    def import_to_workspace(self) -> None:
        if self.workspace is None:
            return
        parent_directory = QFileDialog.getExistingDirectory(
            self, "Choose destination parent directory for package files"
        )
        if not parent_directory:
            return
        project_name = str(self.preview["project"].get("name") or "imported-project")
        safe_default = "".join(
            character if character.isalnum() or character in " -_." else "-"
            for character in project_name
        ).strip(" .") or "imported-project"
        folder_name, accepted = QInputDialog.getText(
            self, "Import project files", "Create a new folder named:",
            text=safe_default,
        )
        if not accepted:
            return
        folder_name = folder_name.strip()
        if (
            not folder_name or Path(folder_name).name != folder_name
            or folder_name in {".", ".."}
        ):
            QMessageBox.warning(
                self, "Invalid folder name",
                "Enter a simple folder name without path separators.",
            )
            return
        try:
            project, extracted = import_workspace_project(
                self.workspace, self.package_path,
                Path(parent_directory) / folder_name,
            )
            if self.on_import is not None:
                self.on_import(project.project_id)
            QMessageBox.information(
                self, "Project imported",
                f"'{project.name}' is now in this workspace.\nFiles: {extracted}",
            )
        except (PackageError, ValueError, OSError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not import project", str(exc))

    def save_report(self) -> None:
        default_name = str(self.preview["project"].get("name") or "handover")
        safe_name = "".join(
            character if character.isalnum() or character in " -_." else "-"
            for character in default_name
        ).strip(" .") or "handover"
        filename, _selected_filter = QFileDialog.getSaveFileName(
            self, "Save handover report", f"{safe_name}-handover.md",
            "Markdown files (*.md);;Text files (*.txt)",
        )
        if not filename:
            return
        try:
            Path(filename).write_text(
                render_handover_report(self.preview), encoding="utf-8"
            )
            QMessageBox.information(self, "Report saved", f"Saved report to:\\n{filename}")
        except OSError as exc:
            QMessageBox.warning(self, "Could not save report", str(exc))

    def extract_files(self) -> None:
        parent_directory = QFileDialog.getExistingDirectory(
            self, "Choose destination parent directory"
        )
        if not parent_directory:
            return
        project_name = str(self.preview["project"].get("name") or "imported-project")
        safe_default = "".join(
            character if character.isalnum() or character in " -_." else "-"
            for character in project_name
        ).strip(" .") or "imported-project"
        folder_name, accepted = QInputDialog.getText(
            self, "Import folder name", "Create a new folder named:",
            text=safe_default,
        )
        if not accepted:
            return
        folder_name = folder_name.strip()
        if not folder_name or Path(folder_name).name != folder_name or folder_name in {".", ".."}:
            QMessageBox.warning(self, "Invalid folder name", "Enter a simple folder name without path separators.")
            return
        try:
            destination = import_package(
                self.package_path, Path(parent_directory) / folder_name
            )
            QMessageBox.information(
                self, "Files extracted",
                f"Verified package files were extracted to:\n{destination}",
            )
        except (PackageError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "Could not extract package", str(exc))


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
        search_button = QPushButton("Search workspace…")
        side_layout.addWidget(search_button)
        side_layout.addWidget(QLabel("WORKSPACE"))
        self.projects = QListWidget()
        side_layout.addWidget(self.projects, 1)
        create = QPushButton("＋  New project")
        create.setObjectName("primary")
        side_layout.addWidget(create)
        create_handover = QPushButton("Create handover package")
        side_layout.addWidget(create_handover)
        backup_button = QPushButton("Back up workspace…")
        restore_button = QPushButton("Restore backup as new workspace…")
        side_layout.addWidget(backup_button)
        side_layout.addWidget(restore_button)
        package_preview = QPushButton("Preview .thread package")
        side_layout.addWidget(package_preview)
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
        search_button.clicked.connect(self.open_search_dialog)
        create_handover.clicked.connect(self.create_handover_package)
        backup_button.clicked.connect(self.backup_current_workspace)
        restore_button.clicked.connect(self.restore_workspace_backup)
        package_preview.clicked.connect(self.open_package_preview)
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

    def open_search_dialog(self) -> None:
        dialog = SearchDialog(self.workspace, on_open=self.refresh_projects, parent=self)
        dialog.exec()

    def backup_current_workspace(self) -> None:
        output, _selected_filter = QFileDialog.getSaveFileName(
            self, "Back up workspace", "yuktara-thread.backup",
            "SQLite backups (*.backup *.sqlite3);;All files (*)",
        )
        if not output:
            return
        destination = Path(output)
        try:
            backup = backup_workspace(self.workspace.database.path, destination)
            QMessageBox.information(
                self, "Workspace backup created",
                f"Verified backup saved to:\n{backup}",
            )
        except (ValueError, OSError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not back up workspace", str(exc))

    def restore_workspace_backup(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self, "Select workspace backup", "",
            "SQLite backups (*.backup *.sqlite3);;All files (*)",
        )
        if not filename:
            return
        destination, _selected_filter = QFileDialog.getSaveFileName(
            self, "Restore as a new workspace database", "restored-workspace.sqlite3",
            "SQLite databases (*.sqlite3);;All files (*)",
        )
        if not destination:
            return
        answer = QMessageBox.question(
            self, "Restore backup",
            "This creates a separate new workspace database. It will not replace or modify "
            "the workspace currently open in this window. Continue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            restored = restore_workspace(Path(filename), Path(destination))
            QMessageBox.information(
                self, "Workspace restored",
                f"Restored database:\n{restored}\n"
                "Close this window and open the restored database to continue there.",
            )
        except (ValueError, OSError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not restore workspace", str(exc))

    def create_handover_package(self) -> None:
        current = self.projects.currentItem()
        if current is None:
            QMessageBox.information(self, "Select a project", "Choose a project before creating a handover.")
            return
        project_id = str(current.data(Qt.ItemDataRole.UserRole))
        source_directory = QFileDialog.getExistingDirectory(
            self, "Choose the files to include in this handover"
        )
        if not source_directory:
            return
        output, _selected_filter = QFileDialog.getSaveFileName(
            self, "Save Thread handover", f"{current.text()}.thread",
            "Thread packages (*.thread)",
        )
        if not output:
            return
        output_path = Path(output)
        if output_path.suffix.lower() != ".thread":
            output_path = output_path.with_suffix(".thread")
        try:
            scan = scan_selected_files(Path(source_directory))
            if scan["finding_count"]:
                lines = [
                    f"{item['path']} · line {item['line']} · {item['rule']}"
                    for item in scan["findings"][:30]
                ]
                if scan["finding_count"] > 30:
                    lines.append(f"…and {scan['finding_count'] - 30} more finding(s)")
                answer = QMessageBox.question(
                    self, "Review possible secrets",
                    "The selected files contain patterns that may be credentials or private keys. "
                    "No matched values are shown. Review the locations below.\n\n"
                    + "\n".join(lines)
                    + "\n\nContinue only if you intentionally want to include these files. "
                    "This heuristic scan can miss secrets.",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if answer != QMessageBox.StandardButton.Yes:
                    return
            package = export_workspace_project(
                self.workspace, project_id, Path(source_directory), output_path
            )
            QMessageBox.information(
                self, "Handover created",
                f"Created {package.name}\n"
                f"{scan['scanned_files']} files scanned · "
                f"{scan['finding_count']} potential secret finding(s).",
            )
        except (PackageError, ValueError, OSError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not create handover", str(exc))

    def open_package_preview(self) -> None:
        filename, _selected_filter = QFileDialog.getOpenFileName(
            self, "Open Thread package", "", "Thread packages (*.thread);;All files (*)"
        )
        if not filename:
            return
        package_path = Path(filename)
        try:
            preview = preview_package(package_path)
            dialog = PackagePreviewDialog(
                package_path, preview, self,
                workspace=self.workspace, on_import=self.refresh_projects,
            )
            dialog.exec()
        except (PackageError, OSError, ValueError) as exc:
            QMessageBox.warning(self, "Invalid package", str(exc))

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
        self.project_page = ProjectPage(
            self.workspace, project,
            on_edit=self.edit_project,
            on_archive=self.archive_project,
        )
        self.pages.addWidget(self.project_page)
        self.pages.setCurrentWidget(self.project_page)

    def edit_project(self, project) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Edit project")
        dialog.setMinimumWidth(440)
        form = QFormLayout(dialog)
        name = QLineEdit(project.name)
        summary = QPlainTextEdit(project.summary)
        summary.setMinimumHeight(100)
        form.addRow("Project name", name)
        form.addRow("Summary", summary)
        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel = QPushButton("Cancel")
        save = QPushButton("Save changes")
        save.setObjectName("primary")
        cancel.clicked.connect(dialog.reject)
        save.clicked.connect(dialog.accept)
        actions.addWidget(cancel)
        actions.addWidget(save)
        form.addRow(actions)
        if dialog.exec() != QDialog.DialogCode.Accepted:
            return
        try:
            updated = self.workspace.update_project(
                project.project_id, name.text(), summary.toPlainText()
            )
            self.refresh_projects(updated.project_id)
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not update project", str(exc))

    def archive_project(self, project) -> None:
        answer = QMessageBox.question(
            self, "Archive project",
            f"Archive '{project.name}'? It will disappear from the active workspace list. Its data will be retained.",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.workspace.archive_project(project.project_id)
            if self.project_page is not None:
                self.pages.removeWidget(self.project_page)
                self.project_page.deleteLater()
                self.project_page = None
            self.refresh_projects()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not archive project", str(exc))
