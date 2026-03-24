# Changelog

All notable changes to this project will be documented in this file.

The format is based on Keep a Changelog and this project adheres to
Semantic Versioning.

------------------------------------------------------------------------

## \[Unreleased\]

### Added

-   Support for reading task title from stdin in `todo add`\
    (e.g. `echo "foo" | todo add`)

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
