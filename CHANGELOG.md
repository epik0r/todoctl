# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to
Semantic Versioning.

------------------------------------------------------------------------

## [Unreleased]

### Added

-   Added a shell reload hint after `todo init` to explain how to activate
    session integration in the current shell
-   Added macOS command `todo ramdisk-create` to create the RAM disk used for
    hardened editing mode

### Changed

-   Introduced a hardened editing mode with RAM-backed temporary files for
    editor sessions
-   Added `security_mode` and `secure_temp_dir` configuration options
-   Increased the default scrypt work factor for newly encrypted data and
    introduced a versioned v2 encrypted blob format while keeping legacy v1
    blobs readable

### Security

-   Removed plaintext passphrase support via `TODOCTL_PASSPHRASE` and sanitize
    the editor subprocess environment to avoid leaking secrets to child
    processes
-   Replaced the predictable PPID-based shell session fallback with a random
    in-memory session identifier
-   Sanitized backup tar metadata to prevent leaking UID, GID, username, group
    name and original timestamps
-   Generated the backup manifest fully in memory to avoid temporary manifest
    file races during concurrent backups
-   Switched encrypted month and check file writes to atomic file replacement
    to reduce the risk of corrupted files on interrupted writes
-   Validated month identifiers in storage path handling instead of relying only
    on CLI-level validation
-   Improved editor hardening for vi/vim by disabling backup, swap and viminfo
    persistence and by using RAM-backed temporary files in hardened mode
-   Enabled hardened mode automatically after successful `todo ramdisk-create`
    on macOS

### Fixed

-   Reported self-uninstall failures explicitly and added guidance for
    `pipx uninstall todoctl`
-   Fixed secure editor command construction for vi/vim compatibility

## \[1.0.8\] - 2026-03-24

### Added

-   Support for reading task title from stdin in `todo add`\
    (e.g. `echo "foo" | todo add`)
-   hide DONE tasks in monthly list unless --done is set

------------------------------------------------------------------------

## \[1.0.7\] - 2026-03-23

### Fixed

-   Fixed behavior of `todo list --all`

------------------------------------------------------------------------

## \[1.0.6\] - 2026-03-23

### Added

-   `todo list --all` to display tasks across all months

------------------------------------------------------------------------

## \[1.0.5\] - 2026-03-20

### Security

-   Fixed GitHub code scanning alert (workflow permissions)

### Added

-   Dependabot configuration for Python dependencies

------------------------------------------------------------------------

## \[1.0.4\] - 2026-03-20

### Added

-   Vim integration improvements (ZZ write support)

------------------------------------------------------------------------

## \[1.0.3\] - 2026-03-20

### Fixed

-   Fixed Vim installation issues

------------------------------------------------------------------------

## \[1.0.2\] - 2026-03-20

### Added

-   Python package publishing support
-   GitHub Actions workflow for PyPI releases

------------------------------------------------------------------------

## \[1.0.1\] - 2026-03-20

### Added

-   Version handling improvements

------------------------------------------------------------------------

## \[1.0.0\] - 2026-03-20

### Added

-   Initial release of todoctl
-   Core CLI commands (`add`, `list`, `edit`, `done`, etc.)
-   Encrypted monthly todo storage
