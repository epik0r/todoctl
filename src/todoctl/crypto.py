"""
Encryption and passphrase handling for todoctl.

This module implements password-based encryption and decryption using
scrypt for key derivation and ChaCha20-Poly1305 for authenticated
encryption. It also manages passphrase prompting and encrypted
password check blobs.
"""
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
    """
    Custom exception for cryptographic errors.

    Raised when encryption or decryption fails due to invalid input,
    incorrect passwords, or corrupted data.
    """
    pass

def _derive_key(passphrase: str, salt: bytes) -> bytes:
    """
    Derive a cryptographic key from a passphrase and salt.

    Uses the scrypt key derivation function with predefined parameters.

    Args:
        passphrase (str): User-provided password.
        salt (bytes): Random salt value.

    Returns:
        bytes: Derived symmetric encryption key.
    """
    return scrypt(passphrase.encode("utf-8"), salt=salt, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P, dklen=KEY_SIZE)

def get_passphrase(*, confirm: bool = False, ttl_hours: int = 8, index_file=None) -> str:
    """
    Retrieve the passphrase from environment, cache, or user input.

    The function checks the environment variable first, then attempts to
    load a cached passphrase. If none is available, it prompts the user.
    Optionally confirms the password and stores it in a session cache.

    Args:
        confirm (bool): Whether to require password confirmation.
        ttl_hours (int): Time-to-live for cached passphrase.
        index_file: Path to the session index file.

    Returns:
        str: The passphrase.

    Raises:
        CryptoError: If input is invalid or required parameters are missing.
    """
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
    """
    Encrypt binary data using a passphrase.

    Generates a random salt and nonce, derives a key using scrypt,
    and encrypts the data with ChaCha20-Poly1305.

    Args:
        plaintext (bytes): Data to encrypt.
        confirm_password (bool): Whether to confirm password input.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bytes: Encrypted blob including metadata.
    """
    passphrase = get_passphrase(confirm=confirm_password, ttl_hours=ttl_hours, index_file=index_file)
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    key = _derive_key(passphrase, salt)
    cipher = ChaCha20Poly1305(key)
    ciphertext = cipher.encrypt(nonce, plaintext, MAGIC + salt)
    return MAGIC + salt + nonce + ciphertext

def decrypt_bytes(blob: bytes, *, ttl_hours: int = 8, index_file=None) -> bytes:
    """
    Decrypt binary data using a passphrase.

    Validates the blob format, extracts metadata, derives the key,
    and attempts decryption.

    Args:
        blob (bytes): Encrypted data blob.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bytes: Decrypted plaintext.

    Raises:
        CryptoError: If the blob is invalid, truncated, or decryption fails.
    """
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
    """
    Encrypt a UTF-8 string.

    Encodes the string and delegates encryption to encrypt_bytes.

    Args:
        plaintext (str): Text to encrypt.
        confirm_password (bool): Whether to confirm password input.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bytes: Encrypted data blob.
    """
    return encrypt_bytes(plaintext.encode("utf-8"), confirm_password=confirm_password, ttl_hours=ttl_hours, index_file=index_file)

def decrypt_text(ciphertext: bytes, *, ttl_hours: int = 8, index_file=None) -> str:
    """
    Decrypt a UTF-8 string.

    Decrypts binary data and decodes it into a string.

    Args:
        ciphertext (bytes): Encrypted data blob.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        str: Decrypted plaintext string.

    Raises:
        CryptoError: If decoding fails or data is invalid.
    """
    plaintext = decrypt_bytes(ciphertext, ttl_hours=ttl_hours, index_file=index_file)
    try:
        return plaintext.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise CryptoError("Wrong password or corrupted data") from exc

def create_check_blob(*, confirm_password: bool = False, ttl_hours: int = 8, index_file=None) -> bytes:
    """
    Create an encrypted password check blob.

    Encrypts a predefined constant to allow later verification of the
    correct passphrase.

    Args:
        confirm_password (bool): Whether to confirm password input.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bytes: Encrypted check blob.
    """
    return encrypt_bytes(CHECK_PLAINTEXT, confirm_password=confirm_password, ttl_hours=ttl_hours, index_file=index_file)

def verify_check_blob(blob: bytes, *, ttl_hours: int = 8, index_file=None) -> bool:
    """
    Verify an encrypted password check blob.

    Attempts to decrypt the blob and compares the result with the
    expected plaintext.

    Args:
        blob (bytes): Encrypted check blob.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bool: True if verification succeeds, False otherwise.
    """
    try:
        plaintext = decrypt_bytes(blob, ttl_hours=ttl_hours, index_file=index_file)
    except CryptoError:
        return False
    return hmac.compare_digest(plaintext, CHECK_PLAINTEXT)
