"""Project workspace page composition."""
from __future__ import annotations

from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QPushButton, QTabWidget, QVBoxLayout, QWidget,
)

from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.ui.context import ContextEditor
from yuktara_thread.ui.panels import ActivityPanel, EntityPanel, ReadinessPanel


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
