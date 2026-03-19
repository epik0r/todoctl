from __future__ import annotations
import json, os
from datetime import datetime, timedelta, timezone
from pathlib import Path
import keyring

SERVICE_NAME = "todoctl-shell-session"
ENV_NAME = "TODOCTL_SESSION_ID"

def session_id() -> str:
    value = os.environ.get(ENV_NAME, "").strip()
    if value:
        return value
    return f"fallback-{os.getppid()}"

def _load_index(index_file: Path) -> list[str]:
    if not index_file.exists():
        return []
    try:
        data = json.loads(index_file.read_text(encoding="utf-8"))
        if isinstance(data, list):
            return [str(item) for item in data]
    except Exception:
        return []
    return []

def _save_index(index_file: Path, keys: list[str]) -> None:
    index_file.parent.mkdir(parents=True, exist_ok=True)
    index_file.write_text(json.dumps(sorted(set(keys)), indent=2), encoding="utf-8")

def store_passphrase(passphrase: str, ttl_hours: int, index_file: Path) -> str:
    sid = session_id()
    expires_at = datetime.now(timezone.utc) + timedelta(hours=ttl_hours)
    payload = {"passphrase": passphrase, "expires_at": expires_at.isoformat(), "session_id": sid}
    keyring.set_password(SERVICE_NAME, sid, json.dumps(payload))
    keys = _load_index(index_file)
    keys.append(sid)
    _save_index(index_file, keys)
    return sid

def load_passphrase() -> str | None:
    sid = session_id()
    raw = keyring.get_password(SERVICE_NAME, sid)
    if not raw:
        return None
    try:
        payload = json.loads(raw)
        expires_at = datetime.fromisoformat(payload["expires_at"])
        if datetime.now(timezone.utc) >= expires_at:
            clear_current_session()
            return None
        if payload.get("session_id") != sid:
            return None
        return str(payload["passphrase"])
    except Exception:
        clear_current_session()
        return None

def clear_current_session() -> None:
    sid = session_id()
    try:
        keyring.delete_password(SERVICE_NAME, sid)
    except Exception:
        pass

def clear_all_sessions(index_file: Path) -> int:
    count = 0
    for sid in _load_index(index_file):
        try:
            keyring.delete_password(SERVICE_NAME, sid)
            count += 1
        except Exception:
            pass
    if index_file.exists():
        index_file.unlink()
    return count

def session_status() -> tuple[str, str]:
    sid = session_id()
    raw = keyring.get_password(SERVICE_NAME, sid)
    if not raw:
        return "INFO", f"no active passphrase cached for shell session {sid[:12]}..."
    try:
        payload = json.loads(raw)
        expires_at = datetime.fromisoformat(payload["expires_at"])
        now = datetime.now(timezone.utc)
        if now >= expires_at:
            clear_current_session()
            return "INFO", "expired shell-session cache removed"
        if payload.get("session_id") != sid:
            return "WARN", "cached session id mismatch"
        remaining = expires_at - now
        return "OK", f"shell-session cache valid for {remaining} on session {sid[:12]}..."
    except Exception:
        clear_current_session()
        return "WARN", "invalid shell-session cache removed"
