# Security Policy

## Status

This repository is an early development foundation. It has not undergone an independent security audit and must not be relied on for sensitive or regulated workflows.

## Reporting

Do not publish exploitable vulnerabilities as public issues. Contact the repository owner privately through GitHub's security advisory mechanism where available.

## Current protections

- ZIP entries are inspected before any extraction.
- Absolute paths, traversal paths, duplicate names and symlinks are rejected.
- Archive entry count, individual file size and total uncompressed size are bounded.
- File contents are hashed with SHA-256 and checked during verification.
- Package verification does not execute archive contents.
- Workspace import validates bounded structured metadata, context revision history and source activity entries before extraction.
- Source activity history is replayed with imported-origin metadata; the UI distinguishes imported entries and does not treat them as authenticated evidence.
- Local heuristic secret scanning runs before selected-file export; findings require explicit user acknowledgement and matched values are not displayed.

## Important limitations

- SHA-256 hashes provide integrity checking, not publisher authentication.
- Packages and workspace backups are not encrypted or digitally signed.
- Secret scanning is heuristic and bounded; it is not malware scanning or DLP. Robust OS-level sandboxing and formal threat-model review remain future work.
- Never assume a verified package is safe to execute or open in another application.
