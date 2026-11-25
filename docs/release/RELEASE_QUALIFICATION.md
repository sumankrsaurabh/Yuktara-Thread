# Yuktara Thread Release Qualification Checklist

This checklist is required before declaring a stable release. Passing CI alone is not release qualification.

## Automated gates

- [ ] Python core test matrix passes on Python 3.11, 3.12 and 3.13.
- [ ] Desktop smoke tests pass on Windows, macOS and Linux.
- [ ] Frozen desktop bundle builds pass on all supported platforms.
- [ ] Wheel and source distribution build; Twine metadata validation passes.
- [ ] Package import/export round-trip tests pass, including context revisions and imported activity history.
- [ ] SQLite migration, backup, restore and retention-purge tests pass.
- [ ] No known failing or skipped release-critical tests.

## Manual platform QA

Perform on a clean user account or clean virtual machine for each platform:

- [ ] Launch the app and create a new workspace through the first-run chooser.
- [ ] Reopen an existing workspace and verify the schema migration path.
- [ ] Create, edit, archive, restore and search projects.
- [ ] Edit context, inspect revision history and restore an earlier revision.
- [ ] Create/edit/delete/restore decisions, tasks, milestones and references.
- [ ] Verify task prerequisites and the dependency map.
- [ ] Filter activity by text, event type and inclusive date range; export JSON and Markdown.
- [ ] Create a handover package, inspect it without extraction, verify it, and import it into a clean workspace.
- [ ] Confirm context revision bodies and imported source activity events remain visible and are marked as imported.
- [ ] Test backup and restore to a new path; confirm existing files are never overwritten.
- [ ] Test Unicode project names, paths with spaces, long filenames, large files and low disk space.
- [ ] Test display scaling and window resizing.\n- [ ] Complete keyboard-only navigation using visible focus indicators on each platform.\n- [ ] Test screen-reader labels, reading order and dialog announcements with platform-native assistive technology.\n- [ ] Verify color contrast and non-color status indicators.
- [ ] Confirm core workflows operate offline.

## Security and data integrity

- [ ] Review the threat model and update it for implemented features.
- [ ] Test archive traversal, duplicate paths, symlinks, non-regular entries and oversized archives.
- [ ] Review secret-scanner false positives and false negatives; never treat it as a guarantee.
- [ ] Confirm import never executes package contents.
- [ ] Confirm source activity imported from a package is visibly unverified and not treated as authenticated evidence.
- [ ] Confirm no automatic network transfer, sync or AI request occurs.
- [ ] Confirm backups and handover packages are protected appropriately; they are currently not encrypted.
- [ ] Review database transaction rollback and recovery behavior.
- [ ] Obtain an independent security review before handling sensitive organizational data.

## Distribution and release

- [ ] Decide licensing and verify all bundled dependency licenses.
- [ ] Produce signed/notarized installers if required for the target release.
- [ ] Publish checksums and release notes for each artifact.
- [ ] Test installation, upgrade and uninstall behavior.
- [ ] Tag the exact verified commit and archive CI artifacts.
- [ ] Publish known limitations and supported platform versions.

## Current release blockers

The repository is still pre-alpha. Portable PyInstaller bundles are unsigned; platform-specific installers and code signing are not yet provided. Encryption, package signatures, independent security review and interactive human QA are not complete. Do not describe the current build as production-ready until the applicable checklist items have been completed and recorded.


## Interrupted or failed workspace imports

Workspace imports extract package files into a new destination before committing project records in a single SQLite transaction. On a handled failure after extraction, the application attempts to remove that destination and verifies whether it is gone.

If the error reports that the extracted files could not be removed automatically:

1. Do not retry into the same destination directory.
2. Open the workspace and confirm that the incoming project was not created. The database transaction should have rolled back; verify the project list before proceeding.
3. Inspect the exact recovery directory reported by the error. Preserve any files you need, then remove the directory or move it aside.
4. Retry the import using a new, empty destination directory.

If the process or machine loses power between publishing the extracted directory and committing the database transaction, this version does not have a durable import journal to reconcile that interruption automatically. Check the workspace and destination directory manually before retrying. Never delete an existing destination unless you have confirmed it belongs to the failed import.
