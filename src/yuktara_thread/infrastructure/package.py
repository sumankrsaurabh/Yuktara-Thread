"""Safe creation and integrity verification for .thread archives.

Verification does not extract or execute package contents.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import zipfile
from pathlib import Path, PurePosixPath
from typing import Any

FORMAT_ID = "yuktara.thread"
FORMAT_VERSION = 1
MAX_ENTRIES = 2_000
MAX_FILE_BYTES = 50 * 1024 * 1024
MAX_TOTAL_BYTES = 250 * 1024 * 1024
MAX_MANIFEST_BYTES = 2 * 1024 * 1024


class PackageError(ValueError):
    """Raised when a package is invalid or unsafe."""


def _safe_archive_name(name: str) -> str:
    if not name or "\\" in name or name.startswith("/"):
        raise PackageError(f"Unsafe archive path: {name!r}")
    path = PurePosixPath(name)
    if path.is_absolute() or any(part in ("", ".", "..") for part in path.parts):
        raise PackageError(f"Unsafe archive path: {name!r}")
    if path.parts and ":" in path.parts[0]:
        raise PackageError(f"Drive-qualified archive path: {name!r}")
    return path.as_posix()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def create_package(input_dir: Path, output_file: Path, project: dict[str, Any]) -> Path:
    """Create a .thread package from a directory and a JSON-compatible project dict."""
    source = input_dir.resolve(strict=True)
    if not source.is_dir():
        raise PackageError("Input path must be a directory")
    output = output_file.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)

    entries: list[tuple[Path, str]] = []
    for candidate in sorted(source.rglob("*")):
        if candidate.is_symlink():
            raise PackageError(f"Symbolic links are not allowed: {candidate}")
        if candidate.is_file():
            relative = candidate.relative_to(source).as_posix()
            archive_name = _safe_archive_name(f"files/{relative}")
            size = candidate.stat().st_size
            if size > MAX_FILE_BYTES:
                raise PackageError(f"File exceeds size limit: {relative}")
            entries.append((candidate, archive_name))
    if len(entries) + 2 > MAX_ENTRIES:
        raise PackageError("Package contains too many files")
    total_size = sum(path.stat().st_size for path, _ in entries)
    if total_size > MAX_TOTAL_BYTES:
        raise PackageError("Package exceeds total uncompressed size limit")

    manifest = {
        "format": FORMAT_ID,
        "format_version": FORMAT_VERSION,
        "project": project,
        "files": [
            {"path": name, "size": path.stat().st_size, "sha256": _sha256_file(path)}
            for path, name in entries
        ],
    }
    manifest_bytes = json.dumps(manifest, ensure_ascii=False, indent=2).encode("utf-8")
    if len(manifest_bytes) > MAX_MANIFEST_BYTES:
        raise PackageError("Manifest exceeds size limit")

    temporary = output.with_name(output.name + ".tmp")
    try:
        with zipfile.ZipFile(temporary, "w", compression=zipfile.ZIP_DEFLATED) as archive:
            archive.writestr("manifest.json", manifest_bytes)
            for path, name in entries:
                archive.write(path, name)
        os.replace(temporary, output)
    finally:
        if temporary.exists():
            temporary.unlink()
    return output


def verify_package(package_file: Path) -> dict[str, Any]:
    """Validate package structure and content hashes without extracting files."""
    if not package_file.is_file():
        raise PackageError("Package file does not exist")
    try:
        with zipfile.ZipFile(package_file, "r") as archive:
            infos = archive.infolist()
            if len(infos) > MAX_ENTRIES:
                raise PackageError("Package contains too many entries")
            names: set[str] = set()
            total_size = 0
            for info in infos:
                name = _safe_archive_name(info.filename)
                if name in names:
                    raise PackageError(f"Duplicate archive path: {name}")
                names.add(name)
                mode = info.external_attr >> 16
                if stat.S_ISLNK(mode):
                    raise PackageError(f"Symbolic link entry is not allowed: {name}")
                if info.file_size > MAX_FILE_BYTES:
                    raise PackageError(f"Entry exceeds size limit: {name}")
                total_size += info.file_size
                if total_size > MAX_TOTAL_BYTES + MAX_MANIFEST_BYTES:
                    raise PackageError("Archive exceeds total uncompressed size limit")
            if "manifest.json" not in names:
                raise PackageError("manifest.json is missing")
            manifest_info = archive.getinfo("manifest.json")
            if manifest_info.file_size > MAX_MANIFEST_BYTES:
                raise PackageError("Manifest exceeds size limit")
            manifest = json.loads(archive.read("manifest.json").decode("utf-8"))
            if not isinstance(manifest, dict):
                raise PackageError("Manifest must be a JSON object")
            if manifest.get("format") != FORMAT_ID:
                raise PackageError("Unrecognized package format")
            if manifest.get("format_version") != FORMAT_VERSION:
                raise PackageError("Unsupported package format version")
            declared = manifest.get("files")
            if not isinstance(declared, list):
                raise PackageError("Manifest files must be a list")
            declared_paths: set[str] = set()
            for item in declared:
                if not isinstance(item, dict):
                    raise PackageError("Invalid file record in manifest")
                path = _safe_archive_name(item.get("path", ""))
                if path == "manifest.json" or path in declared_paths:
                    raise PackageError(f"Duplicate or reserved manifest path: {path}")
                declared_paths.add(path)
                if path not in names:
                    raise PackageError(f"Manifest file is missing: {path}")
                info = archive.getinfo(path)
                if item.get("size") != info.file_size:
                    raise PackageError(f"Size mismatch: {path}")
                expected = item.get("sha256")
                if not isinstance(expected, str) or len(expected) != 64:
                    raise PackageError(f"Invalid SHA-256 value: {path}")
                digest = hashlib.sha256()
                with archive.open(path, "r") as stream:
                    for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                        digest.update(chunk)
                if digest.hexdigest() != expected:
                    raise PackageError(f"SHA-256 mismatch: {path}")
            unexpected = names - declared_paths - {"manifest.json"}
            if unexpected:
                raise PackageError(f"Undeclared archive entries: {', '.join(sorted(unexpected))}")
            return {
                "valid": True,
                "format": FORMAT_ID,
                "format_version": FORMAT_VERSION,
                "file_count": len(declared_paths),
                "project": manifest.get("project", {}),
            }
    except (zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError, KeyError) as exc:
        raise PackageError(f"Invalid package: {exc}") from exc
