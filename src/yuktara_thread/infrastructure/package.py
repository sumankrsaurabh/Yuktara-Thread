"""Safe creation and integrity verification for .thread archives.

Verification does not extract or execute package contents.
"""
from __future__ import annotations

import hashlib
import json
import os
import stat
import shutil
import tempfile
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
    if path.as_posix() != name:
        raise PackageError(f"Non-canonical archive path: {name!r}")
    reserved = {"CON", "PRN", "AUX", "NUL"}
    for part in path.parts:
        if any(ord(character) < 32 or character in '<>:"|?*' for character in part):
            raise PackageError(f"Platform-unsafe archive path: {name!r}")
        if part.endswith((" ", ".")):
            raise PackageError(f"Platform-unsafe archive path: {name!r}")
        stem = part.split(".", 1)[0].upper()
        is_numbered_device = (
            len(stem) == 4 and stem[:3] in {"COM", "LPT"} and stem[3] in "123456789"
        )
        if stem in reserved or is_numbered_device:
            raise PackageError(f"Reserved device name in archive path: {name!r}")
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
                file_type = stat.S_IFMT(mode)
                if stat.S_ISLNK(mode) or file_type not in (0, stat.S_IFREG):
                    raise PackageError(f"Non-regular archive entry is not allowed: {name}")
                if info.is_dir():
                    raise PackageError(f"Directory entries are not supported: {name}")
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
            if not isinstance(manifest.get("project"), dict):
                raise PackageError("Package project metadata must be a JSON object")
            declared = manifest.get("files")
            if not isinstance(declared, list):
                raise PackageError("Manifest files must be a list")
            declared_paths: set[str] = set()
            for item in declared:
                if not isinstance(item, dict):
                    raise PackageError("Invalid file record in manifest")
                raw_path = item.get("path")
                if not isinstance(raw_path, str):
                    raise PackageError("Manifest file path must be a string")
                path = _safe_archive_name(raw_path)
                if not path.startswith("files/") or path == "files":
                    raise PackageError(f"Manifest file must be inside files/: {path}")
                if path == "manifest.json" or path in declared_paths:
                    raise PackageError(f"Duplicate or reserved manifest path: {path}")
                declared_paths.add(path)
                if path not in names:
                    raise PackageError(f"Manifest file is missing: {path}")
                info = archive.getinfo(path)
                declared_size = item.get("size")
                if (not isinstance(declared_size, int) or isinstance(declared_size, bool)
                        or declared_size < 0 or declared_size != info.file_size):
                    raise PackageError(f"Size mismatch or invalid size: {path}")
                expected = item.get("sha256")
                if (not isinstance(expected, str) or len(expected) != 64
                        or any(char not in "0123456789abcdef" for char in expected)):
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


def preview_package(package_file: Path) -> dict[str, Any]:
    """Return a verified, non-extracting preview of a .thread package."""
    verification = verify_package(package_file)
    try:
        with zipfile.ZipFile(package_file, "r") as archive:
            manifest_bytes = archive.read("manifest.json")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"Could not read package preview: {exc}") from exc

    project = manifest.get("project")
    if not isinstance(project, dict):
        raise PackageError("Package project metadata must be a JSON object")

    files = []
    for item in manifest["files"]:
        archive_path = _safe_archive_name(item["path"])
        if not archive_path.startswith("files/") or archive_path == "files":
            raise PackageError(f"Package file must be inside files/: {archive_path}")
        files.append({
            "path": archive_path[len("files/"):],
            "size": item["size"],
            "sha256": item["sha256"],
        })
    files.sort(key=lambda item: item["path"].casefold())
    return {
        **verification,
        "project": project,
        "files": files,
        "manifest_sha256": hashlib.sha256(manifest_bytes).hexdigest(),
    }


def import_package(package_file: Path, destination: Path) -> Path:
    """Safely extract a verified package into a new directory.

    Extraction is staged in a sibling temporary directory. The destination is
    published only after every file has been streamed and its size and digest
    have been checked. Existing destinations are never overwritten.
    """
    preview = preview_package(package_file)
    target = destination.expanduser()
    if not target.name or target.name in {".", ".."}:
        raise PackageError("Import destination must be a new directory path")
    parent = target.parent.resolve(strict=True)
    if not parent.is_dir():
        raise PackageError("Import destination parent must be a directory")
    target = parent / target.name
    if target.exists() or target.is_symlink():
        raise PackageError("Import destination already exists")

    lock = parent / f".{target.name}.thread-import.lock"
    try:
        lock_fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
    except FileExistsError as exc:
        raise PackageError("Another import is already using this destination") from exc
    os.close(lock_fd)

    staging: Path | None = None
    try:
        if target.exists() or target.is_symlink():
            raise PackageError("Import destination already exists")
        staging = Path(tempfile.mkdtemp(prefix=f".{target.name}.thread-", dir=parent))
        with zipfile.ZipFile(package_file, "r") as archive:
            manifest_bytes = archive.read("manifest.json")
            if hashlib.sha256(manifest_bytes).hexdigest() != preview["manifest_sha256"]:
                raise PackageError("Package manifest changed during import")
            manifest = json.loads(manifest_bytes.decode("utf-8"))
            for item in manifest["files"]:
                archive_path = _safe_archive_name(item["path"])
                if not archive_path.startswith("files/") or archive_path == "files":
                    raise PackageError(f"Package file must be inside files/: {archive_path}")
                info = archive.getinfo(archive_path)
                if info.is_dir():
                    raise PackageError(f"Directory entries are not supported: {archive_path}")
                mode = info.external_attr >> 16
                file_type = stat.S_IFMT(mode)
                if file_type not in (0, stat.S_IFREG) or stat.S_ISLNK(mode):
                    raise PackageError(f"Non-regular file entry is not allowed: {archive_path}")

                relative = PurePosixPath(archive_path)
                output = staging.joinpath(*relative.parts)
                output.parent.mkdir(parents=True, exist_ok=True)
                digest = hashlib.sha256()
                written = 0
                with archive.open(info, "r") as source, output.open("xb") as sink:
                    for chunk in iter(lambda: source.read(1024 * 1024), b""):
                        written += len(chunk)
                        if written > item["size"] or written > MAX_FILE_BYTES:
                            raise PackageError(f"Expanded file exceeds declared size: {archive_path}")
                        digest.update(chunk)
                        sink.write(chunk)
                if written != item["size"]:
                    raise PackageError(f"Size mismatch during import: {archive_path}")
                if digest.hexdigest() != item["sha256"]:
                    raise PackageError(f"SHA-256 mismatch during import: {archive_path}")

        if target.exists() or target.is_symlink():
            raise PackageError("Import destination appeared during import")
        os.rename(staging, target)
        staging = None
        return target
    except (OSError, zipfile.BadZipFile, UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise PackageError(f"Package import failed: {exc}") from exc
    finally:
        if staging is not None and staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        try:
            lock.unlink()
        except FileNotFoundError:
            pass
