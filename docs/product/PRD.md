# Product Requirements Document

## Product

**Yuktara Thread** — local-first project continuity and handover.

## Problem

Project knowledge is fragmented across files, chats, tickets, notes and individual memory. When ownership changes, the next person must reconstruct both the work and the reasoning behind it.

## Outcome

A recipient can inspect a portable project handover, understand its state and resume work without requiring a Yuktara account or network connection.

## Primary workflow

1. Create a local project workspace.
2. Capture goals, scope, current state, constraints and handover notes.
3. Record decisions, tasks, milestones and references.
4. Select files and review exclusions.
5. Generate and verify a portable `.thread` package.
6. Transfer it through a channel chosen by the user.
7. Recipient previews the package before importing.
8. Recipient continues work and creates a new version.

## Target users

- Independent developers and freelancers.
- Small software teams.
- IT service and implementation teams.
- Agencies and research/engineering teams (later).

## MVP requirements

- Local project/workspace management.
- Structured project context.
- Decisions, tasks, milestones and references.
- File inclusion/exclusion controls.
- Portable package creation and integrity verification.
- Preview before extraction/import.
- Human-readable handover report.
- Offline operation and transparent privacy controls.

## Non-goals

- Replacing issue trackers, source control or documentation platforms.
- Real-time multiplayer collaboration.
- Automatic cloud synchronization.
- Mandatory accounts.
- Autonomous AI modification of project data.

## Product acceptance criteria

- Core workflows function offline.
- No network transfer occurs without explicit user action.
- Every package file is listed and integrity-checked.
- Package contents are never auto-executed.
- Import is previewed and designed to avoid overwriting existing data silently.
