# todoctl

A CLI-first, encrypted monthly todo manager for nerdy engineers and architects.

---

## Overview

`todoctl` is designed for people who prefer:

- terminal-first workflows
- structured but lightweight task tracking
- full control over their data
- encryption by default

It is **not** a replacement for a team collaboration tool. It is a personal productivity tool.

---

## Features

- 🔐 Password-based encryption (scrypt + ChaCha20-Poly1305)
- 📅 Monthly task separation
- 🧠 Status-driven workflow (OPEN, DOING, SIDE, DONE)
- 🧾 Stable task IDs
- 🧹 Automatic sorting
- ✍️ Native `vim` / `$EDITOR` editing
- 🧩 Shell integration (auto-installed)
- ⚡ Shell completion (auto-installed)
- 🔄 Session-based password caching
- 💾 Backup support
- 🧼 Clean uninstall (`todo purge --uninstall`)

---

## Installation

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
```

---

## First Run Behavior

On the first real `todo` command (e.g. `todo init`), the tool automatically installs:

- shell session integration
- shell completion (bash or zsh)
- vim integration (if `vim` or `vi` is available)

⚠️ Important:
Shell completion will only be active after:

- opening a new terminal, or
- reloading your shell config:

```bash
source ~/.bashrc
# or
source ~/.zshrc
```

---

## Usage

### Initialize

```bash
todo init
```

### List tasks

```bash
todo list
todo list 03
todo list 2026-03
```

### Edit tasks (recommended workflow)

```bash
todo edit
```

### Add a task

```bash
todo add "Implement API integration"
```

### Change status

```bash
todo doing 1
todo done 1
todo open 1
todo side 1
```

### Remove a task

```bash
todo remove 3
```

### Rollover tasks

```bash
todo rollover 03 04
```

### Backup

```bash
todo backup
```

### Doctor

```bash
todo doctor
```

### Purge

```bash
todo purge --yes
todo purge --yes --uninstall
```

---

## Security Model

- scrypt + ChaCha20-Poly1305
- no plaintext storage
- session-scoped cache

---

## Session Cache

- valid per shell
- expires after TTL (default 8h)
- no cross-terminal sharing

---

## Troubleshooting

```bash
cat ~/.local/share/todoctl/bootstrap.log
```

---

## License

MIT
