from __future__ import annotations
import getpass, hmac, os, secrets
from hashlib import scrypt
from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305
from .shell_session_cache import load_passphrase, store_passphrase

MAGIC = b"TODOCTL11"
SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32
SCRYPT_N = 2**14
SCRYPT_R = 8
SCRYPT_P = 1
CHECK_PLAINTEXT = b"todoctl-password-check"

class CryptoError(RuntimeError):
    pass

def _derive_key(passphrase: str, salt: bytes) -> bytes:
    return scrypt(passphrase.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_SIZE)

def get_passphrase(*, confirm: bool = False, ttl_hours: int = 8, index_file=None) -> str:
    env_passphrase = os.environ.get("TODOCTL_PASSPHRASE")
    if env_passphrase:
        return env_passphrase
    cached = load_passphrase()
    if cached:
        return cached
    first = getpass.getpass("todoctl password: ")
    if not first:
        raise CryptoError("Password cannot be empty")
    if confirm:
        second = getpass.getpass("Repeat password: ")
        if not hmac.compare_digest(first, second):
            raise CryptoError("Passwords do not match")
    if index_file is None:
        raise CryptoError("Session index file is required for shell-session caching")
    store_passphrase(first, ttl_hours, index_file)
    return first

def encrypt_bytes(plaintext: bytes, *, confirm_password: bool = False, ttl_hours: int = 8, index_file=None) -> bytes:
    passphrase = get_passphrase(confirm=confirm_password, ttl_hours=ttl_hours, index_file=index_file)
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    key = _derive_key(passphrase, salt)
    cipher = ChaCha20Poly1305(key)
    ciphertext = cipher.encrypt(nonce, plaintext, MAGIC + salt)
    return MAGIC + salt + nonce + ciphertext

def decrypt_bytes(blob: bytes, *, ttl_hours: int = 8, index_file=None) -> bytes:
    if not blob.startswith(MAGIC):
        raise CryptoError("Unsupported or corrupted encrypted file")
    minimum = len(MAGIC) + SALT_SIZE + NONCE_SIZE + 16
    if len(blob) < minimum:
        raise CryptoError("Encrypted file is truncated")
    salt = blob[len(MAGIC):len(MAGIC)+SALT_SIZE]
    nonce = blob[len(MAGIC)+SALT_SIZE:len(MAGIC)+SALT_SIZE+NONCE_SIZE]
    ciphertext = blob[len(MAGIC)+SALT_SIZE+NONCE_SIZE:]
    passphrase = get_passphrase(confirm=False, ttl_hours=ttl_hours, index_file=index_file)
    key = _derive_key(passphrase, salt)
    cipher = ChaCha20Poly1305(key)
    try:
        return cipher.decrypt(nonce, ciphertext, MAGIC + salt)
    except Exception as exc:
        raise CryptoError("Wrong password or corrupted data") from exc

def encrypt_text(plaintext: str, *, confirm_password: bool = False, ttl_hours: int = 8, index_file=None) -> bytes:
    return encrypt_bytes(plaintext.encode("utf-8"), confirm_password=confirm_password, ttl_hours=ttl_hours, index_file=index_file)

def decrypt_text(ciphertext: bytes, *, ttl_hours: int = 8, index_file=None) -> str:
    plaintext = decrypt_bytes(ciphertext, ttl_hours=ttl_hours, index_file=index_file)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CryptoError("Wrong password or corrupted data") from exc

def create_check_blob(*, confirm_password: bool = False, ttl_hours: int = 8, index_file=None) -> bytes:
    return encrypt_bytes(CHECK_PLAINTEXT, confirm_password=confirm_password, ttl_hours=ttl_hours, index_file=index_file)

def verify_check_blob(blob: bytes, *, ttl_hours: int = 8, index_file=None) -> bool:
    try:
        plaintext = decrypt_bytes(blob, ttl_hours=ttl_hours, index_file=index_file)
    except CryptoError:
        return False
    return hmac.compare_digest(plaintext, CHECK_PLAINTEXT)
