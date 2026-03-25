## [1.0.9] - 2026-03-25

### 🚀 Features

- *(init)* Add shell reload hint to activate session integration
- *(security,fs,docs)* Hardened editing, secure file writes and crypto tuning

### 🛡️ Security

- *(security)* Replace predictable PPID-based session id with random fallback
- *(security)* Stop using env passphrase and sanitize editor environment

### 🐛 Bug Fixes

- *(backup)* Sanitize tar metadata to prevent UID/GID and username leakage
- *(security,init,editor)* Hardened editing mode, RAM-backed tempfiles and vim compatibility
- *(macos)* Enable hardened mode after ramdisk creation
- *(crypto)* Version scrypt-encrypted blobs and raise default work factor
- *(store)* Use atomic writes for encrypted month and check files
- *(backup)* Generate manifest in memory and avoid temporary manifest file
- *(uninstall)* Report pip uninstall failures and add pipx guidance
- *(store)* Validate month identifiers in storage path handling
## [1.0.8] - 2026-03-24

### 🚀 Features

- Add CHANGELOG.md

### 💼 Other

- Read todo add from stdin
- Hide DONE tasks in monthly list unless --done is set
## [1.0.7] - 2026-03-23

### 🚀 Features

- Add 'todo list --all' command fix
## [1.0.6] - 2026-03-23

### 🚀 Features

- Add demo
- Add 'todo list --all' command
## [1.0.5] - 2026-03-20

### 🚀 Features

- Add todo l and e for convenience
- Add Dependabot configuration for Python packages

Configure Dependabot to update Python dependencies weekly.

### 💼 Other

- Potential fix for code scanning alert no. 1: Workflow does not contain permissions

Co-authored-by: Copilot Autofix powered by AI <62310815+github-advanced-security[bot]@users.noreply.github.com>
## [1.0.4] - 2026-03-20

### 💼 Other

- Vi features
- Vim ZZ - saved message
## [1.0.3] - 2026-03-20

### 🐛 Bug Fixes

- Fix vim installing
## [1.0.2] - 2026-03-20

### 🚀 Features

- Add GitHub Actions workflow for Python package publishing

This workflow automates the process of uploading a Python package to PyPI when a release is created, including build and publish steps.

### 💼 Other

- Python publishing
## [1.0.1] - 2026-03-20

### 💼 Other

- Init
- Delete setup.py
- Pep8
- Workflow pylint
- Enhance CI workflow with additional pip install and verbose pytest
- Upgrade Python version from 3.10 to 3.11
- Installation
- Version handling

### 🐛 Bug Fixes

- Fix password failure

### 📚 Documentation

- Docstrings
