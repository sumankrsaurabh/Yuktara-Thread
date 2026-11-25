# Contributing to Yuktara Thread

The project is pre-alpha. Discuss substantial product or architectural changes before implementation. Follow the layer boundaries in docs/architecture/SOFTWARE_ARCHITECTURE.md.

## Development setup

Requirements: Python 3.11 or newer.

```bash
python -m venv .venv
# Windows: .venv\\Scripts\\activate
# macOS/Linux:
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e ".[dev,desktop]"
```

Run the complete test suite:

```bash
python -m compileall -q src
python -m pytest
```

Run desktop smoke tests offscreen:

```bash
QT_QPA_PLATFORM=offscreen python -m pytest tests/test_ui_smoke.py -q
```

Build and validate distributions:

```bash
python -m pip install build twine
python -m build
python -m twine check dist/*
```

## Branch and commit conventions

- Create a focused branch from main for each change.
- Use conventional commit prefixes: feat, fix, refactor, test, docs, build, ci, style.
- Keep each commit scoped to one coherent change.
- Do not commit local workspace databases, backups, exported handover packages, credentials or build output.
- Never rewrite an already applied database migration.

## Engineering rules

1. Keep domain logic independent of Qt, SQLite and external services.
2. Keep UI code out of domain and infrastructure modules.
3. Use type hints and focused functions.
4. Validate all data crossing a trust boundary.
5. Never execute files from a handover package.
6. Add tests for bug fixes and new behavior.
7. Use migrations for persistent schema changes; never silently rewrite user data.
8. Do not introduce network calls into core workflows.
9. Document security and compatibility implications.
10. Put validation in domain/application code, not widgets or CLI argument handlers.
11. UI code calls application use cases; it does not issue SQL.
12. Use parameterized SQL and repository-owned transactions.
13. Append activity events in the same transaction as the state change they describe.
14. Context writes must use expected_revision to prevent silent overwrites.
15. Preserve offline behavior. Any future AI/cloud operation must be optional and require explicit per-operation approval.

## Required tests

A pull request that changes behavior should include tests for:
- The normal successful path.
- Invalid input and boundary conditions.
- Recovery behavior where applicable.
- Transaction rollback or no-partial-write behavior for multi-step operations.
- Backward compatibility for existing workspace databases and older .thread packages when relevant.
- Offscreen desktop behavior when UI workflows change.

Database changes require migration tests. Package changes require malformed archive and round-trip tests. Recovery/purge changes require proof that user data is not permanently removed without explicit confirmation.

## Documentation

Update the relevant documents whenever behavior changes:
- README.md for user-visible capabilities.
- docs/development/CLI.md for CLI commands.
- docs/architecture for schema, package or layer changes.
- docs/security/THREAT_MODEL.md and SECURITY.md for security-sensitive changes.
- IMPLEMENTATION_STATUS.md, docs/product/ROADMAP.md and CHANGELOG.md for milestone changes.

## Pull request checklist

- [ ] The change has a clear scope and rationale.
- [ ] Tests cover success, failure and recovery paths.
- [ ] No secrets, private data or generated workspace files are included.
- [ ] Documentation and status files are updated.
- [ ] Python core matrix passes.
- [ ] Windows/macOS/Linux platform smoke checks pass when relevant.
- [ ] Portable bundle and distribution builds pass when relevant.
- [ ] Known limitations and residual risks are stated honestly.
