# Portable Desktop Builds

The **Desktop Bundles** GitHub Actions workflow can produce portable, self-contained desktop bundles for Windows, macOS and Linux.

## Build

Run the workflow manually from GitHub Actions, or push a version tag beginning with v. Each platform uploads a separate workflow artifact and a SHA-256 checksum file:

- Windows: yuktara-thread-windows.zip
- macOS: yuktara-thread-macos.zip containing YuktaraThread.app
- Linux: yuktara-thread-linux.tar.gz

The bundle is created with PyInstaller and includes the Python runtime and PySide6 dependencies. It is a portable application bundle, not a signed installer.

## Launch

The application never chooses a hidden workspace automatically. You can either pass an explicit workspace database path or launch without arguments to open the first-run dialog and choose an existing database or create a new one. Example with an explicit path:

Windows: run YuktaraThread.exe with --database C:\\path\\to\\workspace.sqlite3. Linux: run ./YuktaraThread --database /path/to/workspace.sqlite3. macOS: open YuktaraThread.app --args --database /path/to/workspace.sqlite3.

Use a separate database file for each independent workspace. Back up the database before testing pre-release builds.

## Release limitations

- Builds are not code-signed or notarized.
- Windows installer/MSIX, macOS signed/notarized DMG/PKG and Linux DEB/RPM/AppImage installers are not yet provided.
- The bundle workflow verifies that packaging completes; it does not replace interactive QA on a physical Windows, macOS or Linux desktop.
- Do not use pre-alpha bundles as the only copy of important project data.
- The .thread format is integrity-checked but not encrypted or publisher-authenticated.

For development installs and source-based launch, see the README and CLI guide.
