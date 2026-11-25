"""Context editing and revision-history presentation components."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMessageBox,
    QPlainTextEdit, QPushButton, QVBoxLayout, QWidget,
)

from yuktara_thread.application.workspace import WorkspaceService


class ContextHistoryDialog(QDialog):
    """Inspect context snapshots and restore one as a new current revision."""

    def __init__(self, workspace: WorkspaceService, project_id: str, section_key: str,
                 on_restore=None, parent=None) -> None:
        super().__init__(parent)
        self.on_restore = on_restore
        self.setWindowTitle(f"Context history · {section_key.replace('_', ' ').title()}")
        self.setMinimumSize(680, 500)
        layout = QVBoxLayout(self)
        self.revisions = QListWidget()
        self.revisions.setAccessibleName("Context revision history")
        self.preview = QPlainTextEdit()
        self.preview.setAccessibleName("Selected context revision preview")
        self.preview.setReadOnly(True)
        content_row = QHBoxLayout()
        content_row.addWidget(self.revisions, 1)
        content_row.addWidget(self.preview, 2)
        layout.addLayout(content_row, 1)
        self.history = workspace.context.history(project_id, section_key)
        for entry in self.history:
            item = QListWidgetItem(
                f"Revision {entry['revision']}  ·  {entry['created_at']}"
            )
            item.setData(Qt.ItemDataRole.UserRole, entry)
            self.revisions.addItem(item)
        self.revisions.currentItemChanged.connect(self.show_revision)
        if self.revisions.count():
            self.revisions.setCurrentRow(0)
        actions = QHBoxLayout()
        actions.addStretch(1)
        close = QPushButton("Close")
        restore = QPushButton("Restore as new revision")
        restore.setObjectName("primary")
        close.clicked.connect(self.reject)
        restore.clicked.connect(self.restore_selected)
        actions.addWidget(close)
        actions.addWidget(restore)
        layout.addLayout(actions)

    def show_revision(self, current, _previous=None) -> None:
        self.preview.setPlainText(
            str(current.data(Qt.ItemDataRole.UserRole)["content"]) if current else ""
        )

    def restore_selected(self) -> None:
        item = self.revisions.currentItem()
        if item is None or self.on_restore is None:
            return
        if self.on_restore(str(item.data(Qt.ItemDataRole.UserRole)["content"])):
            self.accept()

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
        self.editor.setAccessibleName(f"{section.title} context editor")
        self.editor.setAccessibleDescription("Edit the project context section. Save creates a new revision.")
        self.editor.setPlaceholderText("Capture the context another person will need...")
        layout.addWidget(self.editor, 1)
        actions = QHBoxLayout()
        history = QPushButton("History…")
        history.setAccessibleName(f"{section.title} revision history")
        save = QPushButton("Save changes")
        save.setAccessibleName(f"Save {section.title} context")
        save.setObjectName("primary")
        history.clicked.connect(self.open_history)
        save.clicked.connect(self.save)
        actions.addWidget(history)
        actions.addStretch(1)
        actions.addWidget(save)
        layout.addLayout(actions)

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


    def open_history(self) -> None:
        dialog = ContextHistoryDialog(
            self.workspace, self.project_id, self.section_key,
            on_restore=self.restore_revision, parent=self,
        )
        dialog.exec()

    def restore_revision(self, content: str) -> bool:
        try:
            section = self.workspace.save_context(
                self.project_id, self.section_key, content,
                expected_revision=self.revision,
            )
            self.revision = section.revision
            self.editor.setPlainText(section.content)
            QMessageBox.information(
                self, "Revision restored",
                f"Previous content restored as revision {section.revision}.",
            )
            return True
        except (ValueError, LookupError, RuntimeError) as exc:
            QMessageBox.warning(self, "Could not restore revision", str(exc))
            return False
