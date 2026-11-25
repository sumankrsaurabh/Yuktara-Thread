# Yuktara Thread

**Keep the work. Keep the reasoning. Continue without losing context.**

Yuktara Thread is a local-first project continuity and handover platform. It is designed to preserve the context behind a project—decisions, rationale, tasks, milestones, references and selected files—so another person can understand and continue the work.

> **Development status:** early foundation / pre-alpha. This repository is not a production-ready release. The current implementation is a small, standard-library Python core for creating and verifying portable handover packages. The full desktop application and planned modules are not yet implemented.

## Product principles

- Local-first and usable offline.
- No account or cloud service required for core workflows.
- No automatic synchronization or silent data transfer.
- AI is optional and must be explicitly approved for each transfer.
- Portable, inspectable `.thread` packages with SHA-256 integrity checks.
- Importing a package must never execute its contents.

## Current foundation

- Python 3.11+
- Standard-library core; no mandatory runtime dependencies.
- Versioned ZIP-based `.thread` package.
- Manifest and SHA-256 verification.
- Archive path, duplicate-entry, symlink, file-count and size checks.
- CLI commands to create and verify packages.
- Unit tests for package creation and verification.

## Quick start

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install -e ".[dev]"
thread create --input examples/sample-project --output sample.thread
thread verify sample.thread
pytest
```

If installing the package is not desired, run the CLI module with `python -m yuktara_thread.cli` after setting `PYTHONPATH=src`.

## Repository map

- `src/yuktara_thread/domain`: framework-independent domain models.
- `src/yuktara_thread/infrastructure`: package serialization and verification.
- `src/yuktara_thread/cli`: command-line interface.
- `tests`: automated tests.
- `docs`: product, architecture, security and roadmap documentation.
- `examples`: safe sample project context.

## Roadmap

1. Reliable package core and test coverage.
2. Local workspace, SQLite persistence and migrations.
3. Decisions, tasks, milestones, references and append-only history.
4. Desktop UI (PySide6) with UI/application/domain separation.
5. Import preview, transactional import and human-readable reports.
6. Privacy controls, optional AI adapters and platform packaging.

See [IMPLEMENTATION_STATUS.md](IMPLEMENTATION_STATUS.md), [PRD](docs/product/PRD.md), and [architecture](docs/architecture/OVERVIEW.md).

## Security

Package verification checks integrity, not publisher identity. Do not treat an unsigned package as trusted merely because its hashes verify. Never open untrusted attachments outside an appropriate sandbox. See [SECURITY.md](SECURITY.md).

## License

This project is currently marked **All rights reserved** pending a deliberate open-source licensing decision. See [LICENSE](LICENSE).
