"""Main desktop workspace window and application navigation."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QFormLayout, QFrame, QHBoxLayout, QInputDialog, QFileDialog,
    QLabel, QLineEdit, QListWidget, QListWidgetItem, QMainWindow, QMessageBox,
    QPushButton, QPlainTextEdit, QStackedWidget, QVBoxLayout, QWidget,
)

from yuktara_thread.application.backup import backup_workspace, restore_workspace
from yuktara_thread.application.handover import export_workspace_project
from yuktara_thread.application.secret_scan import scan_selected_files
from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.infrastructure.package import PackageError, preview_package
from yuktara_thread.ui.context import ContextEditor, ContextHistoryDialog
from yuktara_thread.ui.dialogs import (
    ArchivedProjectsDialog, PackagePreviewDialog, SearchDialog,
)
from yuktara_thread.ui.pages import ProjectPage
from yuktara_thread.ui.panels import (
    ActivityPanel, DeletedRecordsDialog, EntityEditorDialog, EntityPanel,
    ReadinessPanel, TaskDependencyGraphDialog,
)


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
        archived_button = QPushButton("Archived projects…")
        side_layout.addWidget(archived_button)
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
        archived_button.clicked.connect(self.open_archived_projects)
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

    def open_archived_projects(self) -> None:
        dialog = ArchivedProjectsDialog(
            self.workspace, on_restored=self.refresh_projects, parent=self
        )
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
