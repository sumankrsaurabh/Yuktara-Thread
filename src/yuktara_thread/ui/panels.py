"""Project intelligence, activity, readiness and dependency graph panels."""
from __future__ import annotations

from datetime import datetime
from pathlib import Path
import json

from PySide6.QtCore import Qt
from PySide6.QtGui import QBrush, QColor, QPen
from PySide6.QtWidgets import (
    QComboBox, QDialog, QFormLayout, QHBoxLayout, QFileDialog, QLabel,
    QLineEdit, QListWidget, QListWidgetItem, QMessageBox, QPushButton,
    QPlainTextEdit, QGraphicsView, QGraphicsScene, QVBoxLayout, QWidget,
)

from yuktara_thread.application.readiness import assess_handover_readiness
from yuktara_thread.application.workspace import WorkspaceService


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
            widget.setAccessibleName(label)
            widget.setAccessibleDescription(f"{kind.title()} {label.lower()} field")
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

class DeletedRecordsDialog(QDialog):
    """Review and restore soft-deleted records for one project entity type."""

    def __init__(self, workspace: WorkspaceService, project_id: str, kind: str,
                 on_restored=None, parent=None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.project_id = project_id
        self.kind = kind
        self.on_restored = on_restored
        self.setWindowTitle(f"Deleted {kind}s")
        self.setMinimumSize(520, 380)
        layout = QVBoxLayout(self)
        self.records = QListWidget()
        self.records.setAccessibleName(f"Deleted {kind} records")
        layout.addWidget(self.records, 1)
        self.status = QLabel("Deleted records can be restored without losing their identity.")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        actions.addStretch(1)
        close = QPushButton("Close")
        restore = QPushButton("Restore selected")
        restore.setObjectName("primary")
        close.clicked.connect(self.reject)
        restore.clicked.connect(self.restore_selected)
        actions.addWidget(close)
        actions.addWidget(restore)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        self.records.clear()
        id_column = self.workspace.intelligence.TABLES[self.kind][1]
        for record in self.workspace.intelligence.list_records(
            self.project_id, self.kind, include_deleted=True
        ):
            if record.get("deleted_at") is None:
                continue
            item = QListWidgetItem(
                f"{record['title']}  ·  deleted {record.get('deleted_at') or ''}"
            )
            item.setData(Qt.ItemDataRole.UserRole, record[id_column])
            self.records.addItem(item)
        self.status.setText(
            f"{self.records.count()} deleted record(s). Restore keeps the original record ID."
            if self.records.count() else "There are no deleted records of this type."
        )

    def restore_selected(self) -> None:
        item = self.records.currentItem()
        if item is None:
            return
        entity_id = str(item.data(Qt.ItemDataRole.UserRole))
        answer = QMessageBox.question(
            self, "Restore record",
            "Restore this record to the active project?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if answer != QMessageBox.StandardButton.Yes:
            return
        try:
            self.workspace.restore_record(self.project_id, self.kind, entity_id)
            self.refresh()
            if self.on_restored is not None:
                self.on_restored()
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not restore record", str(exc))

class TaskDependencyGraphDialog(QDialog):
    """Read-only layered view of task prerequisites and downstream work."""

    def __init__(self, workspace: WorkspaceService, project_id: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Task dependency map")
        self.setMinimumSize(820, 560)
        layout = QVBoxLayout(self)
        self.scene = QGraphicsScene(self)
        self.view = QGraphicsView(self.scene)
        layout.addWidget(self.view, 1)
        self.node_items = {}
        tasks = workspace.intelligence.list_records(project_id, "task")
        by_id = {str(task["task_id"]): task for task in tasks}
        prerequisites = {
            task_id: [
                dependency for dependency in workspace.intelligence.list_task_dependencies(task_id)
                if dependency in by_id
            ]
            for task_id in by_id
        }
        depth_cache = {}

        def depth(task_id: str) -> int:
            if task_id not in depth_cache:
                depth_cache[task_id] = (
                    0 if not prerequisites[task_id]
                    else 1 + max(depth(item) for item in prerequisites[task_id])
                )
            return depth_cache[task_id]

        levels = {}
        for task_id in by_id:
            levels.setdefault(depth(task_id), []).append(task_id)
        positions = {}
        for level, task_ids in levels.items():
            for index, task_id in enumerate(task_ids):
                positions[task_id] = (70 + level * 270, 60 + index * 132)

        # Draw prerequisite arrows behind the task cards.
        for task_id, required_ids in prerequisites.items():
            x, y = positions[task_id]
            for required_id in required_ids:
                rx, ry = positions[required_id]
                line = self.scene.addLine(
                    rx + 196, ry + 38, x, y + 38,
                    QPen(QColor("#8A94A6"), 2),
                )
                line.setZValue(0)

        for task_id, task in by_id.items():
            x, y = positions[task_id]
            card = self.scene.addRect(
                x, y, 196, 76,
                QPen(QColor("#C8CDD5"), 1),
                QBrush(QColor("#FFFFFF")),
            )
            card.setZValue(1)
            label = self.scene.addText(
                f"{task['title']}\n{str(task.get('status', 'open')).replace('_', ' ').title()}"
            )
            label.setDefaultTextColor(QColor("#20242B"))
            label.setTextWidth(176)
            label.setPos(x + 10, y + 10)
            label.setZValue(2)
            self.node_items[task_id] = card

        if not tasks:
            self.scene.addText("No active tasks yet. Add tasks to build a dependency map.")
        width = max((x for x, _y in positions.values()), default=0) + 300
        height = max((y for _x, y in positions.values()), default=0) + 180
        self.scene.setSceneRect(0, 0, max(width, 520), max(height, 260))
        note = QLabel(
            "Lines connect each prerequisite to the task that depends on it. "
            "This view is read-only; edit relationships in the Tasks tab."
        )
        note.setObjectName("muted")
        note.setWordWrap(True)
        layout.addWidget(note)
        close = QPushButton("Close")
        close.clicked.connect(self.accept)
        layout.addWidget(close, 0, Qt.AlignmentFlag.AlignRight)

class EntityPanel(QWidget):
    """Full-field CRUD editor for decisions, tasks, milestones and references."""

    def __init__(self, workspace: WorkspaceService, project_id: str, kind: str) -> None:
        super().__init__()
        self.workspace = workspace
        self.project_id = project_id
        self.kind = kind
        self.list = QListWidget()
        self.list.setAccessibleName(f"{kind.title()} records")
        self.list.setAccessibleDescription(f"Active {kind} records for this project.")
        layout = QVBoxLayout(self)
        description = QLabel(
            "Capture enough detail for another person to understand and continue this work."
        )
        description.setObjectName("muted")
        layout.addWidget(description)
        layout.addWidget(self.list, 1)
        actions = QHBoxLayout()
        add = QPushButton(f"Add {kind}")
        add.setAccessibleName(f"Add {kind}")
        edit = QPushButton("Edit details")
        edit.setAccessibleName(f"Edit selected {kind}")
        delete = QPushButton("Delete")
        delete.setAccessibleName(f"Delete selected {kind}")
        recover = QPushButton("Deleted records…")
        recover.setAccessibleName(f"Review deleted {kind} records")
        add.setObjectName("primary")
        actions.addWidget(add)
        actions.addStretch(1)
        actions.addWidget(recover)
        if self.kind == "task":
            graph = QPushButton("Dependency map…")
            actions.addWidget(graph)
            graph.clicked.connect(self.open_dependency_graph)
        actions.addWidget(edit)
        actions.addWidget(delete)
        layout.addLayout(actions)
        add.clicked.connect(self.add_record)
        edit.clicked.connect(self.edit_record)
        delete.clicked.connect(self.delete_record)
        recover.clicked.connect(self.open_deleted_records)

        self.dependency_list = None
        self.prerequisite_picker = None
        if self.kind == "task":
            dependency_heading = QLabel("Task prerequisites")
            dependency_heading.setStyleSheet("font-weight: 600;")
            layout.addWidget(dependency_heading)
            dependency_row = QHBoxLayout()
            self.prerequisite_picker = QComboBox()
            self.prerequisite_picker.setAccessibleName("Choose prerequisite task")
            self.prerequisite_picker.setPlaceholderText("Select a prerequisite task")
            add_dependency = QPushButton("Add prerequisite")
            remove_dependency = QPushButton("Remove selected")
            dependency_row.addWidget(self.prerequisite_picker, 1)
            dependency_row.addWidget(add_dependency)
            dependency_row.addWidget(remove_dependency)
            layout.addLayout(dependency_row)
            self.dependency_list = QListWidget()
            self.dependency_list.setAccessibleName("Prerequisites of selected task")
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

    def open_dependency_graph(self) -> None:
        dialog = TaskDependencyGraphDialog(
            self.workspace, self.project_id, parent=self
        )
        dialog.exec()

    def open_deleted_records(self) -> None:
        dialog = DeletedRecordsDialog(
            self.workspace, self.project_id, self.kind,
            on_restored=self.refresh, parent=self,
        )
        dialog.exec()
        self.refresh()
        if self.kind == "task":
            self.refresh_dependencies()

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
    """Readable, searchable and type-filterable paginated project activity stream."""

    PAGE_SIZE = 100

    LABELS = {
        "project.created": "Project created",
        "project.updated": "Project details updated",
        "project.archived": "Project archived",
        "project.restored": "Project restored",
        "handover.imported": "Handover imported",
        "context.updated": "Context updated",
        "decision.created": "Decision added",
        "decision.updated": "Decision updated",
        "decision.deleted": "Decision deleted",
        "decision.restored": "Decision restored",
        "task.created": "Task added",
        "task.updated": "Task updated",
        "task.deleted": "Task deleted",
        "task.restored": "Task restored",
        "task.dependency_added": "Task prerequisite added",
        "task.dependency_removed": "Task prerequisite removed",
        "milestone.created": "Milestone added",
        "milestone.updated": "Milestone updated",
        "milestone.deleted": "Milestone deleted",
        "milestone.restored": "Milestone restored",
        "reference.created": "Reference added",
        "reference.updated": "Reference updated",
        "reference.deleted": "Reference deleted",
        "reference.restored": "Reference restored",
    }

    def __init__(self, workspace: WorkspaceService, project_id: str) -> None:
        super().__init__()
        self.workspace = workspace
        self.project_id = project_id
        self.events = workspace.intelligence.timeline(project_id, limit=self.PAGE_SIZE)
        self.has_more = len(self.events) == self.PAGE_SIZE

        layout = QVBoxLayout(self)
        filters = QHBoxLayout()
        self.search = QLineEdit()
        self.search.setPlaceholderText("Search activity...")
        self.kind_filter = QComboBox()
        self.kind_filter.setAccessibleName("Filter activity by event type")
        self.kind_filter.addItem("All activity", "")
        event_types = sorted({str(event["event_type"]) for event in self.events})
        for event_type in event_types:
            self.kind_filter.addItem(self.LABELS.get(event_type, event_type), event_type)
        self.date_from = QLineEdit()
        self.date_from.setAccessibleName("Activity start date, inclusive")
        self.date_from.setPlaceholderText("From YYYY-MM-DD")
        self.date_to = QLineEdit()
        self.date_to.setAccessibleName("Activity end date, inclusive")
        self.date_to.setPlaceholderText("To YYYY-MM-DD")
        filters.addWidget(self.search, 1)
        filters.addWidget(self.kind_filter)
        filters.addWidget(self.date_from)
        filters.addWidget(self.date_to)
        layout.addLayout(filters)

        self.list = QListWidget()
        self.list.setAccessibleName("Filtered project activity")
        self.list.setAccessibleDescription("Activity entries matching the current filters.")
        layout.addWidget(self.list, 1)
        footer = QHBoxLayout()
        self.filter_status = QLabel("Dates are inclusive. Leave blank for no date bound.")
        self.filter_status.setObjectName("muted")
        self.load_older = QPushButton("Load older activity")
        self.load_older.setAccessibleName("Load older project activity")
        refresh = QPushButton("Refresh")
        export = QPushButton("Export activity…")
        footer.addWidget(self.filter_status, 1)
        footer.addWidget(self.load_older)
        footer.addWidget(refresh)
        footer.addWidget(export)
        layout.addLayout(footer)
        refresh.clicked.connect(self.refresh_events)
        self.load_older.clicked.connect(self.load_older_events)
        self.search.textChanged.connect(self.apply_filters)
        self.kind_filter.currentIndexChanged.connect(self.apply_filters)
        self.date_from.textChanged.connect(self.apply_filters)
        self.date_to.textChanged.connect(self.apply_filters)
        export.clicked.connect(self.export_activity)
        self._update_pagination_controls()
        self.apply_filters()

    def _update_pagination_controls(self) -> None:
        self.load_older.setEnabled(self.has_more)
        self.load_older.setText("Load older activity" if self.has_more else "All activity loaded")

    def refresh_events(self) -> None:
        selected_type = self.kind_filter.currentData()
        self.events = self.workspace.intelligence.timeline(
            self.project_id, limit=self.PAGE_SIZE
        )
        self.has_more = len(self.events) == self.PAGE_SIZE
        self.kind_filter.blockSignals(True)
        self.kind_filter.clear()
        self.kind_filter.addItem("All activity", "")
        for event_type in sorted({str(event["event_type"]) for event in self.events}):
            self.kind_filter.addItem(self.LABELS.get(event_type, event_type), event_type)
        if selected_type:
            index = self.kind_filter.findData(selected_type)
            if index >= 0:
                self.kind_filter.setCurrentIndex(index)
        self.kind_filter.blockSignals(False)
        self._update_pagination_controls()
        self.apply_filters()

    def load_older_events(self) -> None:
        if not self.has_more or not self.events:
            return
        oldest = self.events[-1]
        page = self.workspace.intelligence.timeline(
            self.project_id, limit=self.PAGE_SIZE,
            before=(str(oldest["created_at"]), str(oldest["event_id"])),
        )
        self.events.extend(page)
        for event_type in sorted({str(event["event_type"]) for event in page}):
            if self.kind_filter.findData(event_type) < 0:
                self.kind_filter.addItem(self.LABELS.get(event_type, event_type), event_type)
        self.has_more = len(page) == self.PAGE_SIZE
        self._update_pagination_controls()
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
        start_date = self.date_from.text().strip()
        end_date = self.date_to.text().strip()
        try:
            for value in (start_date, end_date):
                if value:
                    datetime.strptime(value, "%Y-%m-%d")
            if start_date and end_date and start_date > end_date:
                raise ValueError("Start date must not be after end date.")
        except ValueError:
            self.filter_status.setText("Enter valid dates (YYYY-MM-DD); start must not be after end.")
            self.list.clear()
            return
        self.filter_status.setText(
            f"Showing {len(self.events)} loaded events. Dates are inclusive; load older activity to search further back."
        )
        self.list.clear()
        for event in self.events:
            event_type = str(event["event_type"])
            label = self.LABELS.get(event_type, event_type.replace(".", " ").title())
            if (event.get("payload") or {}).get("_origin") == "imported":
                label += " · imported"
            detail = self._description(event)
            timestamp = str(event["created_at"])
            event_date = timestamp[:10]
            searchable = f"{label} {detail} {timestamp}".casefold()
            if selected_type and event_type != selected_type:
                continue
            if query and query not in searchable:
                continue
            if start_date and event_date < start_date:
                continue
            if end_date and event_date > end_date:
                continue
            item = QListWidgetItem(f"{label}  ·  {timestamp}\n{detail}".rstrip())
            item.setData(Qt.ItemDataRole.UserRole, event)
            self.list.addItem(item)

    def export_activity(self) -> None:
        events = [
            self.list.item(index).data(Qt.ItemDataRole.UserRole)
            for index in range(self.list.count())
        ]
        if not events:
            QMessageBox.information(self, "No activity", "There is no visible activity to export.")
            return
        filename, selected_filter = QFileDialog.getSaveFileName(
            self, "Export filtered activity", "project-activity.json",
            "JSON files (*.json);;Markdown files (*.md)",
        )
        if not filename:
            return
        path = Path(filename)
        try:
            if path.suffix.lower() == ".md" or "Markdown" in selected_filter:
                lines = ["# Project activity", ""]
                for event in events:
                    event_type = str(event["event_type"])
                    label = self.LABELS.get(event_type, event_type.replace(".", " ").title())
                    imported = (event.get("payload") or {}).get("_origin") == "imported"
                    if imported:
                        label += " · imported"
                    lines.extend([
                        f"## {label}", "",
                        f"- When: {event['created_at']}",
                        f"- Origin: {'Imported (unverified)' if imported else 'Local workspace'}",
                        f"- Type: {event_type}",
                        f"- Entity: {event.get('entity_type', '')}",
                        f"- ID: {event.get('entity_id') or ''}",
                        f"- Details: {self._description(event) or '—'}", "",
                    ])
                path = path.with_suffix(".md")
                path.write_text("\n".join(lines), encoding="utf-8")
            else:
                path = path.with_suffix(".json")
                path.write_text(
                    json.dumps(events, ensure_ascii=False, indent=2), encoding="utf-8"
                )
            QMessageBox.information(self, "Activity exported", f"Saved {len(events)} event(s) to:\n{path}")
        except OSError as exc:
            QMessageBox.warning(self, "Could not export activity", str(exc))

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
