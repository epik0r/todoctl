# Security Policy

## Overview

todoctl is a CLI-first encrypted personal task manager with a strong focus on local security.

Core principles:
- Encryption by default
- No plaintext persistence (when hardened mode is enabled)
- Minimal attack surface
- Explicit, user-controlled security features

---

## Threat Model

todoctl is designed to protect against:

- Accidental data leakage on disk
- Other processes reading environment variables
- Exposure through backups or logs
- Weak password handling practices

It is NOT designed to protect against:

- Full system compromise
- Malware running under the same user with full access
- Memory scraping attacks

---

## Key Security Features

### Encryption

- ChaCha20-Poly1305 (AEAD)
- scrypt for key derivation
- Versioned encrypted blobs (future-proof)

### Passphrase Handling

- No environment variable support (e.g. TODOCTL_PASSPHRASE removed)
- Secure prompt via getpass
- Session-based caching via system keyring
- Random session identifiers

### File Safety

- Atomic file writes (prevent corruption)
- Strict path validation
- Sanitized backup metadata

### Editor Isolation

- Sanitized environment for subprocesses
- Optional hardened mode for editing
- vi/vim hardened flags (no swap, no backup, no history)

---

## Hardened Editing Mode (Recommended)

Hardened mode ensures that decrypted content:

- is only stored in RAM
- is not written to disk
- is wiped after editing

### Setup

macOS:
```bash
todo ramdisk-create
```

Linux:
Use `/dev/shm` or another RAM-backed filesystem.

### Why this matters

Without hardened mode:
- temp files may persist on disk
- editor swap files may leak data

With hardened mode:
- no disk persistence
- reduced forensic recovery risk

---

## Recommended Configuration

- Enable hardened mode
- Use strong passphrases
- Keep system keyring secured
- Regularly update todoctl

---

## Reporting Security Issues

If you discover a vulnerability:

1. Do NOT open a public issue immediately
2. Contact the maintainer privately
3. Provide reproduction steps

---

## Disclaimer

todoctl provides strong local security guarantees but depends on the underlying OS security model.
