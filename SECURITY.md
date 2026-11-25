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

## Important limitations

- SHA-256 hashes provide integrity checking, not publisher authentication.
- Packages are not encrypted or digitally signed.
- Secret scanning, malware scanning, robust import isolation and a formal threat-model review remain future work.
- Never assume a verified package is safe to execute or open in another application.
