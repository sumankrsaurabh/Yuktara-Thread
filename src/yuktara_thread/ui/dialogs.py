"""Workspace search, package preview and archive recovery dialogs."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QInputDialog, QFileDialog, QLabel, QLineEdit,
    QListWidget, QListWidgetItem, QMessageBox, QPushButton, QPlainTextEdit,
    QVBoxLayout, QWidget,
)

from yuktara_thread.application.handover import (
    export_workspace_project, import_workspace_project, inspect_workspace_import,
)
from yuktara_thread.application.handover_report import render_handover_report
from yuktara_thread.application.search import search_workspace
from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.infrastructure.package import PackageError, import_package, preview_package


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
        self.results = QListWidget()\n        self.results.setAccessibleName("Workspace search results")
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

        self.file_list = QPlainTextEdit()\n        self.file_list.setAccessibleName("Verified package file inventory")
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
        try:
            inspection = inspect_workspace_import(self.workspace, self.package_path)
        except (PackageError, ValueError, OSError) as exc:
            QMessageBox.warning(self, "Could not inspect import", str(exc))
            return
        candidates = inspection["candidate_projects"]
        collisions = inspection["record_collisions"]
        details = []
        if candidates:
            details.append(
                "Possible matching project(s): "
                + ", ".join(
                    f"{item['name']} ({item['status']}; {item['match_reason'].replace('_', ' ')})"
                    for item in candidates
                )
            )
        if collisions:
            details.append(
                "Matching record titles: "
                + "; ".join(
                    f"{item['entity_type']}: {', '.join(item['titles'])}"
                    for item in collisions
                )
            )
        if details:
            message = (
                "This package resembles existing workspace content.\n\n"
                + "\n".join(details)
                + "\n\nImport will still create a separate project. "
                "No existing records will be merged, changed or replaced. "
                "Continue?"
            )
            choice = QMessageBox.warning(
                self, "Potential import conflicts", message,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if choice != QMessageBox.StandardButton.Yes:
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

class ArchivedProjectsDialog(QDialog):
    """Inspect archived projects and restore them to the active workspace."""

    def __init__(self, workspace: WorkspaceService, on_restored=None, parent=None) -> None:
        super().__init__(parent)
        self.workspace = workspace
        self.on_restored = on_restored
        self.setWindowTitle("Archived projects")
        self.setMinimumSize(480, 360)
        layout = QVBoxLayout(self)
        self.projects = QListWidget()
        self.projects.itemDoubleClicked.connect(lambda _item: self.restore_selected())
        layout.addWidget(self.projects, 1)
        self.status = QLabel("Archived projects are retained until you restore them.")
        self.status.setObjectName("muted")
        layout.addWidget(self.status)
        actions = QHBoxLayout()
        actions.addStretch(1)
        close = QPushButton("Close")
        restore = QPushButton("Restore project")
        restore.setObjectName("primary")
        close.clicked.connect(self.reject)
        restore.clicked.connect(self.restore_selected)
        actions.addWidget(close)
        actions.addWidget(restore)
        layout.addLayout(actions)
        self.refresh()

    def refresh(self) -> None:
        self.projects.clear()
        archived = self.workspace.list_projects(include_archived=True)
        for project in archived:
            if project.status != "archived":
                continue
            item = QListWidgetItem(f"{project.name}  ·  {project.archived_at or 'Archived'}")
            item.setData(Qt.ItemDataRole.UserRole, project.project_id)
            self.projects.addItem(item)
        self.status.setText(
            f"{self.projects.count()} archived project(s). Restoring preserves their existing data and activity history."
            if self.projects.count() else "There are no archived projects."
        )

    def restore_selected(self) -> None:
        item = self.projects.currentItem()
        if item is None:
            return
        project_id = str(item.data(Qt.ItemDataRole.UserRole))
        try:
            project = self.workspace.restore_project(project_id)
            self.refresh()
            if self.on_restored is not None:
                self.on_restored(project.project_id)
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not restore project", str(exc))
