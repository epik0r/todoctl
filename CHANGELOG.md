# Changelog

All notable changes to this project will be documented in this file.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
and this project adheres to [Semantic Versioning](https://semver.org/).

---

## [1.0.9] - 2026-03-25

### 🚀 Added
- Shell reload hint after `todo init` to activate session integration
- macOS command `todo ramdisk-create` for RAM disk setup (hardened mode)

### 🔄 Changed
- Introduced hardened editing mode with RAM-backed temporary files
- Added `security_mode` and `secure_temp_dir` configuration options
- Introduced versioned encrypted blob format (v2)
- Adjusted default scrypt work factor for stability and compatibility

### 🔐 Security
- Removed `TODOCTL_PASSPHRASE` environment variable support
- Sanitized editor subprocess environment to prevent secret leakage
- Replaced predictable PPID-based session IDs with secure random identifiers
- Sanitized backup metadata (UID, GID, names, timestamps)
- Generated backup manifests fully in memory
- Switched to atomic file writes for encrypted data
- Added strict validation for month identifiers
- Hardened vi/vim editor behavior (no swap, backup, or history)
- Enabled hardened mode automatically after `todo ramdisk-create` on macOS

### 🐛 Fixed
- Improved uninstall error reporting and pipx guidance
- Fixed secure editor command construction for vi/vim compatibility

---

## [1.0.8] - 2026-03-24

### 🚀 Added
- Support reading task title from stdin (`echo "foo" | todo add`)
- Hide DONE tasks unless `--done` is specified

---

## [1.0.7] - 2026-03-23

### 🐛 Fixed
- Fixed behavior of `todo list --all`

---

## [1.0.6] - 2026-03-23

### 🚀 Added
- `todo list --all` to display tasks across all months

---

## [1.0.5] - 2026-03-20

### 🔐 Security
- Fixed GitHub code scanning alert (workflow permissions)

### 🚀 Added
- Dependabot configuration for Python dependencies

---

## [1.0.4] - 2026-03-20

### 🚀 Added
- Vim integration improvements (ZZ write support)

---

## [1.0.3] - 2026-03-20

### 🐛 Fixed
- Fixed Vim installation issues

---

## [1.0.2] - 2026-03-20

### 🚀 Added
- Python package publishing support
- GitHub Actions workflow for PyPI releases

---

## [1.0.1] - 2026-03-20

### 🚀 Added
- Version handling improvements

---

## [1.0.0] - 2026-03-20

### 🚀 Added
- Initial release of todoctl
- Core CLI commands (`add`, `list`, `edit`, `done`, etc.)
- Encrypted monthly todo storage
