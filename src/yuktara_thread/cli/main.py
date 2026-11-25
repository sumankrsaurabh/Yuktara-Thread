"""Command-line entry point for packages and local workspaces."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path

from yuktara_thread.application.backup import backup_workspace, restore_workspace
from yuktara_thread.application.handover import (\n    export_workspace_project, import_workspace_project, reconcile_workspace_imports,\n)
from yuktara_thread.application.workspace import WorkspaceService
from yuktara_thread.application.secret_scan import scan_selected_files
from yuktara_thread.application.search import search_workspace
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

    workspace = commands.add_parser("workspace", help="Initialize, back up or restore a local workspace")
    workspace.add_argument("action", choices=["init", "backup", "restore"])
    workspace.add_argument("--database", required=True, type=Path,
                           help="Workspace database path; for restore, this must be a new destination")
    workspace.add_argument("--output", type=Path,
                           help="New backup file path (required for backup)")
    workspace.add_argument("--backup", type=Path,
                           help="Existing backup file path (required for restore)")

    import_recovery = commands.add_parser(
        "import-recovery",
        help="Reconcile interrupted workspace handover imports without deleting data",
    )
    import_recovery.add_argument("--database", required=True, type=Path)

    search = commands.add_parser("search", help="Search local workspace project context and records")
    search.add_argument("--database", required=True, type=Path)
    search.add_argument("--query", required=True)
    search.add_argument("--limit", type=int, default=50)
    search.add_argument("--include-archived", action="store_true")

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
    project_restore = project_actions.add_parser("restore", help="Restore an archived project")
    project_restore.add_argument("--database", required=True, type=Path)
    project_restore.add_argument("--project-id", required=True)
    project_export = project_actions.add_parser("export", help="Compile a workspace project into a .thread package")
    project_export.add_argument("--database", required=True, type=Path)
    project_export.add_argument("--project-id", required=True)
    project_export.add_argument("--files", required=True, type=Path,
                                help="Directory containing explicitly selected handover files")
    project_export.add_argument("--output", required=True, type=Path)
    project_export.add_argument("--allow-potential-secrets", action="store_true",
                                help="Proceed after reviewing local potential-secret warnings")
    project_import = project_actions.add_parser("import", help="Import a .thread handover into the workspace")
    project_import.add_argument("--database", required=True, type=Path)
    project_import.add_argument("--package", required=True, type=Path)
    project_import.add_argument("--files-destination", required=True, type=Path)
    record = commands.add_parser("record", help="Recover soft-deleted project records")
    record_actions = record.add_subparsers(dest="record_action", required=True)
    deleted_records = record_actions.add_parser("list-deleted", help="List deleted records in a project")
    deleted_records.add_argument("--database", required=True, type=Path)
    deleted_records.add_argument("--project-id", required=True)
    deleted_records.add_argument("--entity-type", required=True, choices=["decision", "task", "milestone", "reference"])
    record_restore = record_actions.add_parser("restore", help="Restore a deleted project record")
    record_restore.add_argument("--database", required=True, type=Path)
    record_restore.add_argument("--project-id", required=True)
    record_restore.add_argument("--entity-type", required=True, choices=["decision", "task", "milestone", "reference"])
    record_restore.add_argument("--entity-id", required=True)
    purge_records = record_actions.add_parser(
        "purge-deleted", help="Dry-run or permanently purge old soft-deleted records"
    )
    purge_records.add_argument("--database", required=True, type=Path)
    purge_records.add_argument("--project-id", required=True)
    purge_records.add_argument("--entity-type", required=True, choices=["decision", "task", "milestone", "reference"])
    purge_records.add_argument("--older-than-days", required=True, type=int)
    purge_records.add_argument(
        "--confirm", action="store_true",
        help="Permanently remove eligible records after reviewing the dry-run count",
    )

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
            if args.action == "init":
                workspace = WorkspaceService(args.database)
                print(json.dumps({"initialized": True, "schema_version": workspace.schema_version,
                                  "database": str(args.database)}, indent=2))
                return 0
            if args.action == "backup":
                if args.output is None:
                    raise ValueError("workspace backup requires --output")
                backup = backup_workspace(args.database, args.output)
                print(json.dumps({"backed_up": True, "database": str(args.database),
                                  "backup": str(backup)}, indent=2))
                return 0
            if args.action == "restore":
                if args.backup is None:
                    raise ValueError("workspace restore requires --backup")
                restored = restore_workspace(args.backup, args.database)
                print(json.dumps({"restored": True, "backup": str(args.backup),
                                  "database": str(restored)}, indent=2))
                return 0
        if args.command == "import-recovery":
            workspace = WorkspaceService(args.database)
            results = reconcile_workspace_imports(workspace)
            print(json.dumps({
                "reconciled_count": len(results),
                "imports": results,
                "note": "No files or project records were deleted. Review recovery_required entries manually.",
            }, indent=2, ensure_ascii=False))
            return 0
        if args.command == "search":
            workspace = WorkspaceService(args.database)
            results = search_workspace(
                workspace, args.query, limit=args.limit,
                include_archived=args.include_archived,
            )
            print(json.dumps({
                "query": args.query, "result_count": len(results),
                "results": results,
            }, indent=2, ensure_ascii=False))
            return 0
        if args.command == "desktop":
            from yuktara_thread.ui.app import run as run_desktop
            return run_desktop(args.database)
        if args.command == "record":
            workspace = WorkspaceService(args.database)
            if args.record_action == "list-deleted":
                records = workspace.intelligence.list_records(
                    args.project_id, args.entity_type, include_deleted=True
                )
                deleted = [item for item in records if item.get("deleted_at") is not None]
                print(json.dumps(deleted, indent=2, ensure_ascii=False))
                return 0
            if args.record_action == "restore":
                restored = workspace.restore_record(
                    args.project_id, args.entity_type, args.entity_id
                )
                print(json.dumps({"restored": True, "record": restored}, indent=2, ensure_ascii=False))
                return 0
            if args.record_action == "purge-deleted":
                result = workspace.purge_deleted_records(
                    args.project_id, args.entity_type,
                    older_than_days=args.older_than_days,
                    confirm=args.confirm,
                )
                print(json.dumps(result, indent=2, ensure_ascii=False))
                return 0
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
            if args.project_action == "restore":
                project = workspace.restore_project(args.project_id)
                print(json.dumps({"project_id": project.project_id, "status": project.status},
                                 indent=2))
                return 0
            if args.project_action == "export":
                secret_scan = scan_selected_files(args.files)
                if secret_scan["finding_count"] and not args.allow_potential_secrets:
                    print(json.dumps({
                        "exported": False,
                        "requires_confirmation": True,
                        "message": "Potential secrets were found. Review the paths and rules; rerun with --allow-potential-secrets only if you intend to include them.",
                        "secret_scan": secret_scan,
                    }, indent=2, ensure_ascii=False))
                    return 3
                package_path = export_workspace_project(
                    workspace, args.project_id, args.files, args.output
                )
                print(json.dumps({
                    "exported": True, "project_id": args.project_id,
                    "package": str(package_path), "secret_scan": secret_scan,
                }, indent=2, ensure_ascii=False))
                return 0
            if args.project_action == "import":
                project, extracted = import_workspace_project(
                    workspace, args.package, args.files_destination
                )
                print(json.dumps({
                    "imported": True, "project_id": project.project_id,
                    "name": project.name, "files": str(extracted),
                }, indent=2, ensure_ascii=False))
                return 0
    except (PackageError, ValueError, OSError, LookupError, RuntimeError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
