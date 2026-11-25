# Architecture Overview

## Architectural style

A modular monolith with a Python-first core. Do not introduce microservices for the desktop MVP.

## Layers

- **Domain:** entities, value objects, validation and domain rules. No Qt, SQL or network dependencies.
- **Application:** use cases and orchestration. Depends on domain abstractions.
- **Infrastructure:** SQLite repositories, filesystem adapters and package serialization.
- **Presentation:** PySide6 windows, screens, view models and design system.
- **AI adapters:** optional providers behind a narrow interface and an explicit consent gate.

## Planned source boundaries

```text
src/yuktara_thread/
  domain/
    projects/
    decisions/
    tasks/
    milestones/
    references/
    events/
  application/
    projects/
    decisions/
    tasks/
    workspace/
    packages/
  infrastructure/
    database/
      migrations/
      repositories/
    filesystem/
    packages/
  presentation/
    windows/
    screens/
    components/
    viewmodels/
    theme/
  ai/
    providers/
    consent/
  bootstrap/
  cli/
```

The current repository implements only a small initial subset. Do not create empty abstractions just to mimic the planned tree; add modules when their use cases are implemented.

## Persistence

SQLite is the planned local database. Use explicit, ordered migrations and foreign keys. UI components must never issue SQL directly. Operations that mutate state and append project events must share a transaction.

## Package boundary

The `.thread` format is a versioned ZIP container with a JSON manifest and SHA-256 digests. Verify paths, entry counts, sizes and hashes before import. Verification is not authentication.

## UI

PySide6 is the planned cross-platform desktop toolkit. Keep it outside the domain layer. A minimal, restrained interface should prioritize legibility, predictable navigation and clear data-transfer consent.

## Platform targets

Windows, Linux and macOS. Packaging, signing and OS-specific integration are future milestones.
