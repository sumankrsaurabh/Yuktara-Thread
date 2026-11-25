"""Command-line entry point."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from yuktara_thread.domain.models import ProjectContext
from yuktara_thread.infrastructure.package import PackageError, create_package, verify_package


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="thread", description="Yuktara Thread project handover tools")
    commands = parser.add_subparsers(dest="command", required=True)

    create = commands.add_parser("create", help="Create a .thread package")
    create.add_argument("--input", required=True, type=Path, help="Directory containing project files")
    create.add_argument("--output", required=True, type=Path, help="Output .thread file")
    create.add_argument("--name", default=None, help="Project name (defaults to input directory name)")
    create.add_argument("--summary", default="", help="Short project summary")

    verify = commands.add_parser("verify", help="Verify a .thread package")
    verify.add_argument("package", type=Path)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "create":
            name = args.name or args.input.name
            project = ProjectContext.create(name, args.summary)
            result = create_package(args.input, args.output, project.to_dict())
            print(f"Created package: {result}")
            return 0
        if args.command == "verify":
            result = verify_package(args.package)
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
    except (PackageError, ValueError, OSError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
