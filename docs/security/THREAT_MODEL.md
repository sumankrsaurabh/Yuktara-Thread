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
- Local pre-export secret heuristics report only file paths, line numbers and rule identifiers; potential matches are never printed. CLI export stops on findings unless the user supplies an explicit override after review.
- No extraction or execution during verification or preview.
- Staged extraction into a new destination directory; existing destinations are not overwritten.
- Manifest recheck and per-file size/hash recheck while extracting; failed staging directories are removed.
- Workspace import validates metadata and dependency graphs before extraction, then restores database records in one transaction; a failed database transaction removes the newly extracted directory.
- Package creation uses a unique temporary file, verifies the completed archive before publishing it and rejects output paths inside the selected source directory.

## Planned mitigations

- Local heuristic scanning for common credential/private-key patterns before workspace export; explicit user acknowledgement is required to proceed when findings exist.
- Import conflict resolution, merge/replace workflows and full source activity-history replay.
- Explicit provider/data/retention consent before AI transfer.
- Optional authenticated encryption and digital signatures using established libraries.
- Security tests, dependency review and external assessment.

## Residual risk

The secret scan is heuristic, bounded and best-effort: it can miss secrets in unsupported encodings, binary files, oversized files or unrecognized formats, and it can flag harmless text. It is not a DLP system. The current foundation is not audited. It does not encrypt packages, authenticate publishers, detect malware or guarantee safety of files after a user opens them. Use only non-sensitive test data during early development.
