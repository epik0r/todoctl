"""
Encryption and passphrase handling for todoctl.

This module implements password-based encryption and decryption using
scrypt for key derivation and ChaCha20-Poly1305 for authenticated
encryption. It also manages passphrase prompting and encrypted
password check blobs.
"""
from __future__ import annotations

import getpass
import hmac
import secrets
from hashlib import scrypt

from cryptography.hazmat.primitives.ciphers.aead import ChaCha20Poly1305

from .shell_session_cache import clear_current_session, load_passphrase, store_passphrase

MAGIC_V1 = b"TODOCTL11"
MAGIC_V2 = b"TODOCTL12"

SALT_SIZE = 16
NONCE_SIZE = 12
KEY_SIZE = 32

LEGACY_SCRYPT_N = 2**14
LEGACY_SCRYPT_R = 8
LEGACY_SCRYPT_P = 1

DEFAULT_SCRYPT_N = 2**14
DEFAULT_SCRYPT_R = 8
DEFAULT_SCRYPT_P = 1

CHECK_PLAINTEXT = b"todoctl-password-check"


class CryptoError(RuntimeError):
    """
    Custom exception for cryptographic errors.

    Raised when encryption or decryption fails due to invalid input,
    incorrect passwords, or corrupted data.
    """


def _derive_key(passphrase: str, salt: bytes, *, n: int, r: int, p: int) -> bytes:
    """
    Derive a cryptographic key from a passphrase and salt.

    Uses the scrypt key derivation function with caller-provided parameters.

    Args:
        passphrase (str): User-provided password.
        salt (bytes): Random salt value.
        n (int): CPU and memory cost parameter.
        r (int): Block size parameter.
        p (int): Parallelization parameter.

    Returns:
        bytes: Derived symmetric encryption key.
    """
    return scrypt(
        passphrase.encode("utf-8"),
        salt=salt,
        n=n,
        r=r,
        p=p,
        dklen=KEY_SIZE,
    )


def _encode_scrypt_params(*, n: int, r: int, p: int) -> bytes:
    """
    Encode scrypt parameters into a fixed-size binary header.

    The N parameter is stored as log2(N), while r and p are stored as
    single-byte unsigned integers.

    Args:
        n (int): CPU and memory cost parameter.
        r (int): Block size parameter.
        p (int): Parallelization parameter.

    Returns:
        bytes: Three-byte parameter block.

    Raises:
        CryptoError: If parameters are unsupported or invalid.
    """
    if n < 2 or (n & (n - 1)) != 0:
        raise CryptoError("Invalid scrypt parameter N")
    if not (1 <= r <= 255):
        raise CryptoError("Invalid scrypt parameter r")
    if not (1 <= p <= 255):
        raise CryptoError("Invalid scrypt parameter p")

    log_n = n.bit_length() - 1
    if 2**log_n != n:
        raise CryptoError("Invalid scrypt parameter N")
    if not (1 <= log_n <= 63):
        raise CryptoError("Invalid scrypt parameter N")

    return bytes([log_n, r, p])


def _decode_scrypt_params(data: bytes) -> tuple[int, int, int]:
    """
    Decode scrypt parameters from a fixed-size binary header.

    Args:
        data (bytes): Three-byte parameter block.

    Returns:
        tuple[int, int, int]: Decoded (n, r, p) values.

    Raises:
        CryptoError: If the parameter block is invalid.
    """
    if len(data) != 3:
        raise CryptoError("Invalid encrypted file header")

    log_n, r, p = data
    if log_n < 1:
        raise CryptoError("Invalid encrypted file header")
    if r < 1 or p < 1:
        raise CryptoError("Invalid encrypted file header")

    return 2**log_n, r, p


def get_passphrase(*, confirm: bool = False, ttl_hours: int = 8, index_file=None) -> str:
    """
    Retrieve the passphrase from cache or user input.

    The function first attempts to load a cached passphrase. If none is
    available, it prompts the user. Optionally confirms the password and
    stores it in a session cache.

    Environment variables are intentionally not accepted as a passphrase
    source because process environments are visible to child processes and
    may be inspectable by other processes of the same user.

    Args:
        confirm (bool): Whether to require password confirmation.
        ttl_hours (int): Time-to-live for cached passphrase.
        index_file: Path to the session index file.

    Returns:
        str: The passphrase.

    Raises:
        CryptoError: If input is invalid or required parameters are missing.
    """
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

    New encryptions use version 2 of the blob format, which embeds the
    scrypt parameters in the header to allow future parameter changes
    without breaking compatibility.

    Args:
        plaintext (bytes): Data to encrypt.
        confirm_password (bool): Whether to confirm password input.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bytes: Encrypted blob including metadata.
    """
    passphrase = get_passphrase(
        confirm=confirm_password,
        ttl_hours=ttl_hours,
        index_file=index_file,
    )
    salt = secrets.token_bytes(SALT_SIZE)
    nonce = secrets.token_bytes(NONCE_SIZE)
    params = _encode_scrypt_params(
        n=DEFAULT_SCRYPT_N,
        r=DEFAULT_SCRYPT_R,
        p=DEFAULT_SCRYPT_P,
    )
    key = _derive_key(
        passphrase,
        salt,
        n=DEFAULT_SCRYPT_N,
        r=DEFAULT_SCRYPT_R,
        p=DEFAULT_SCRYPT_P,
    )
    cipher = ChaCha20Poly1305(key)
    aad = MAGIC_V2 + params + salt
    ciphertext = cipher.encrypt(nonce, plaintext, aad)
    return MAGIC_V2 + params + salt + nonce + ciphertext


def decrypt_bytes(blob: bytes, *, ttl_hours: int = 8, index_file=None) -> bytes:
    """
    Decrypt binary data using a passphrase.

    Supports both the legacy v1 blob format and the current v2 format.

    Args:
        blob (bytes): Encrypted data blob.
        ttl_hours (int): Cache duration for the passphrase.
        index_file: Path to the session index file.

    Returns:
        bytes: Decrypted plaintext.

    Raises:
        CryptoError: If the blob is invalid, truncated, or decryption fails.
    """
    passphrase = get_passphrase(confirm=False, ttl_hours=ttl_hours, index_file=index_file)

    if blob.startswith(MAGIC_V2):
        header_len = len(MAGIC_V2) + 3 + SALT_SIZE + NONCE_SIZE + 16
        if len(blob) < header_len:
            raise CryptoError("Encrypted file is truncated")

        params_raw = blob[len(MAGIC_V2):len(MAGIC_V2) + 3]
        salt_start = len(MAGIC_V2) + 3
        salt_end = salt_start + SALT_SIZE
        nonce_end = salt_end + NONCE_SIZE

        n, r, p = _decode_scrypt_params(params_raw)
        salt = blob[salt_start:salt_end]
        nonce = blob[salt_end:nonce_end]
        ciphertext = blob[nonce_end:]

        key = _derive_key(passphrase, salt, n=n, r=r, p=p)
        cipher = ChaCha20Poly1305(key)

        try:
            return cipher.decrypt(nonce, ciphertext, MAGIC_V2 + params_raw + salt)
        except Exception as exc:
            clear_current_session()
            raise CryptoError("Wrong password or corrupted data") from exc

    if blob.startswith(MAGIC_V1):
        minimum = len(MAGIC_V1) + SALT_SIZE + NONCE_SIZE + 16
        if len(blob) < minimum:
            raise CryptoError("Encrypted file is truncated")

        salt = blob[len(MAGIC_V1):len(MAGIC_V1) + SALT_SIZE]
        nonce = blob[len(MAGIC_V1) + SALT_SIZE:len(MAGIC_V1) + SALT_SIZE + NONCE_SIZE]
        ciphertext = blob[len(MAGIC_V1) + SALT_SIZE + NONCE_SIZE:]

        key = _derive_key(
            passphrase,
            salt,
            n=LEGACY_SCRYPT_N,
            r=LEGACY_SCRYPT_R,
            p=LEGACY_SCRYPT_P,
        )
        cipher = ChaCha20Poly1305(key)

        try:
            return cipher.decrypt(nonce, ciphertext, MAGIC_V1 + salt)
        except Exception as exc:
            clear_current_session()
            raise CryptoError("Wrong password or corrupted data") from exc

    raise CryptoError("Unsupported or corrupted encrypted file")


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
    return encrypt_bytes(
        plaintext.encode("utf-8"),
        confirm_password=confirm_password,
        ttl_hours=ttl_hours,
        index_file=index_file,
    )


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
    return encrypt_bytes(
        CHECK_PLAINTEXT,
        confirm_password=confirm_password,
        ttl_hours=ttl_hours,
        index_file=index_file,
    )


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
