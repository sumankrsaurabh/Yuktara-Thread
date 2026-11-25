# Initial Threat Model

## Assets

- Project notes, decisions and handover context.
- Selected project files and metadata.
- Local workspace database.
- User-controlled package exports.

## Threats

- Malicious archive paths or symlink entries.
- ZIP bombs and resource exhaustion.
- Tampered package contents.
- Accidental inclusion of credentials or private files.
- Silent data transfer to an AI/cloud provider.
- Accidental overwrite during import.
- Treating integrity verification as proof of identity.

## Current mitigations

- Canonical archive path validation, traversal rejection and Windows-reserved-name rejection.
- Symlink, special-file, directory-entry and duplicate-entry rejection.
- File-count and uncompressed-size limits.
- SHA-256 verification of every declared file.
- No extraction or execution during verification or preview.
- Staged extraction into a new destination directory; existing destinations are not overwritten.
- Manifest recheck and per-file size/hash recheck while extracting; failed staging directories are removed.

## Planned mitigations

- Secret scanning and inclusion review.
- Import conflict resolution, merge/replace workflows and full source activity-history replay.
- Explicit provider/data/retention consent before AI transfer.
- Optional authenticated encryption and digital signatures using established libraries.
- Security tests, dependency review and external assessment.

## Residual risk

The current foundation is not audited. It does not encrypt packages, authenticate publishers, detect malware or guarantee safety of files after a user opens them. Use only non-sensitive test data during early development.
