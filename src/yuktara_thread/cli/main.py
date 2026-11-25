"""Command-line entry point for packages and local workspaces."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from yuktara_thread.application.handover import export_workspace_project
from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.domain.models import ProjectContext
from yuktara_thread.infrastructure.package import (
    PackageError, create_package, import_package, preview_package, verify_package,
)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thread", description="Yuktara Thread tools")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a .thread handover package")
    create.add_argument("--input", required=True, type=Path)
    create.add_argument("--output", required=True, type=Path)
    create.add_argument("--name")
    create.add_argument("--summary", default="")

    verify = commands.add_parser("verify", help="Verify a .thread package")
    verify.add_argument("package", type=Path)

    preview = commands.add_parser("preview", help="Preview a verified .thread package without extracting it")
    preview.add_argument("package", type=Path)

    package_import = commands.add_parser("import", help="Safely import a .thread package into a new directory")
    package_import.add_argument("package", type=Path)
    package_import.add_argument("--destination", required=True, type=Path)

    workspace = commands.add_parser("workspace", help="Initialize a local workspace")
    workspace.add_argument("action", choices=["init"])
    workspace.add_argument("--database", required=True, type=Path)

    desktop = commands.add_parser("desktop", help="Open the native desktop workspace")
    desktop.add_argument("--database", required=True, type=Path,
                         help="Path to the local SQLite workspace database")

    project = commands.add_parser("project", help="Manage local workspace projects")
    project_actions = project.add_subparsers(dest="project_action", required=True)
    project_create = project_actions.add_parser("create", help="Create a project")
    project_create.add_argument("--database", required=True, type=Path)
    project_create.add_argument("--name", required=True)
    project_create.add_argument("--summary", default="")
    project_list = project_actions.add_parser("list", help="List projects")
    project_list.add_argument("--database", required=True, type=Path)
    project_list.add_argument("--include-archived", action="store_true")
    project_archive = project_actions.add_parser("archive", help="Archive a project")
    project_archive.add_argument("--database", required=True, type=Path)
    project_archive.add_argument("--project-id", required=True)
    project_export = project_actions.add_parser("export", help="Compile a workspace project into a .thread package")
    project_export.add_argument("--database", required=True, type=Path)
    project_export.add_argument("--project-id", required=True)
    project_export.add_argument("--files", required=True, type=Path,
                                help="Directory containing explicitly selected handover files")
    project_export.add_argument("--output", required=True, type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            project = ProjectContext.create(args.name or args.input.name, args.summary)
            path = create_package(args.input, args.output, project.to_dict())
            print(f"Created package: {path}")
            return 0
        if args.command == "verify":
            print(json.dumps(verify_package(args.package), indent=2, ensure_ascii=False))
            return 0
        if args.command == "preview":
            preview = preview_package(args.package)
            preview.pop("manifest_sha256", None)
            print(json.dumps(preview, indent=2, ensure_ascii=False))
            return 0
        if args.command == "import":
            destination = import_package(args.package, args.destination)
            print(json.dumps({"imported": True, "destination": str(destination)}, indent=2))
            return 0
        if args.command == "workspace":
            workspace = WorkspaceService(args.database)
            print(json.dumps({"initialized": True, "schema_version": workspace.schema_version,
                              "database": str(args.database)}, indent=2))
            return 0
        if args.command == "desktop":
            from yuktara_thread.ui.app import run as run_desktop
            return run_desktop(args.database)
        if args.command == "project":
            workspace = WorkspaceService(args.database)
            if args.project_action == "create":
                project = workspace.create_project(args.name, args.summary)
                print(json.dumps({
                    "project_id": project.project_id, "name": project.name,
                    "summary": project.summary, "status": project.status,
                }, indent=2, ensure_ascii=False))
                return 0
            if args.project_action == "list":
                projects = workspace.list_projects(args.include_archived)
                print(json.dumps([
                    {"project_id": p.project_id, "name": p.name, "summary": p.summary,
                     "status": p.status, "updated_at": p.updated_at}
                    for p in projects
                ], indent=2, ensure_ascii=False))
                return 0
            if args.project_action == "archive":
                project = workspace.archive_project(args.project_id)
                print(json.dumps({"project_id": project.project_id, "status": project.status},
                                 indent=2))
                return 0
            if args.project_action == "export":
                package_path = export_workspace_project(
                    workspace, args.project_id, args.files, args.output
                )
                print(json.dumps({
                    "exported": True, "project_id": args.project_id,
                    "package": str(package_path),
                }, indent=2, ensure_ascii=False))
                return 0
    except (PackageError, ValueError, OSError, LookupError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
