# Contributing

The project is in early pre-alpha. Discuss substantial changes before implementation.

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

## Local development

```bash
python -m pip install -e ".[dev]"
pytest
```

## Commit convention

Use concise imperative messages, for example:
- `Add package manifest validation`
- `Prevent archive path traversal`
