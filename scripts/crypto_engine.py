# -*- coding: utf-8 -*-
"""AES-256-GCM containers for FlightCheckPy database files."""

import os
from pathlib import Path

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes

MAGIC = b"FCP1"
SALT_LEN = 16
NONCE_LEN = 12
TAG_LEN = 16
PBKDF2_ROUNDS = 100_000
MIN_MASTER_KEY_BYTES = 32
MIN_ENVELOPE_LEN = len(MAGIC) + SALT_LEN + NONCE_LEN + TAG_LEN

PROJECT_ROOT = Path(__file__).resolve().parents[1]
MASTER_KEY_PATH = PROJECT_ROOT / "resources" / ".master_key"
MASTER_PASSPHRASE_SALT = b"FlightCheckPy.master.salt.v1"
MASTER_PASSPHRASE_PEPPER = b"FlightCheckPy.master.pepper.v1"


class CryptoFormatError(ValueError):
    """Encrypted file header does not match the FCP1 container."""

    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(message)


def master_key_is_strong(master_password: str) -> bool:
    return len(master_password.encode("utf-8")) >= MIN_MASTER_KEY_BYTES


def resolve_master_key() -> str:
    """Return the user-supplied master secret.

    The secret comes from FCP_MASTER_KEY or from resources/.master_key after
    the user saves a passphrase. Nothing is generated when both are absent.
    """
    env_key = os.environ.get("FCP_MASTER_KEY", "").strip()
    if env_key:
        _require_strong_key(env_key)
        return env_key
    if MASTER_KEY_PATH.is_file():
        file_key = MASTER_KEY_PATH.read_text(encoding="utf-8").strip()
        if file_key:
            _require_strong_key(file_key)
            return file_key
    return ""


def write_master_key(secret: str) -> Path:
    """Write a master secret the user chose. The file is not created automatically."""
    text = secret.strip()
    _require_strong_key(text)
    MASTER_KEY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MASTER_KEY_PATH.write_text(text + "\n", encoding="utf-8")
    return MASTER_KEY_PATH


def stretch_master_passphrase(passphrase: str) -> str:
    """Stretch a short passphrase into a 256-bit key with the project salt and pepper.

    The stored value is the hex form of that key, so the same passphrase always
    produces the same master secret.
    """
    material = MASTER_PASSPHRASE_PEPPER + passphrase.encode("utf-8")
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=MASTER_PASSPHRASE_SALT,
        iterations=PBKDF2_ROUNDS,
    )
    return kdf.derive(material).hex()


def save_master_passphrase(passphrase: str) -> Path:
    """Store a user passphrase. Passphrases under 32 bytes are stretched first."""
    text = passphrase.strip()
    if not text:
        raise ValueError("Master passphrase is empty")
    secret = text if master_key_is_strong(text) else stretch_master_passphrase(text)
    return write_master_key(secret)


def encrypted_header_ok(path: Path) -> bool:
    """True when the file is large enough and starts with the FCP1 magic.

    This reads four bytes. It does not decrypt the database.
    """
    if not path.is_file():
        return False
    try:
        if path.stat().st_size < MIN_ENVELOPE_LEN:
            return False
        with path.open("rb") as handle:
            return handle.read(len(MAGIC)) == MAGIC
    except OSError:
        return False


def derive_key(master_password: str, salt: bytes) -> bytes:
    """Derive a 256-bit AES key from the master secret and a per-file salt."""
    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=32,
        salt=salt,
        iterations=PBKDF2_ROUNDS,
    )
    return kdf.derive(master_password.encode("utf-8"))


def encrypt_sqlite_payload(sqlite_bytes: bytes, master_password: str) -> bytes:
    """Encrypt a SQLite image as MAGIC + salt + nonce + ciphertext + tag."""
    _require_strong_key(master_password)
    salt = os.urandom(SALT_LEN)
    nonce = os.urandom(NONCE_LEN)
    aesgcm = AESGCM(derive_key(master_password, salt))
    ciphertext_and_tag = aesgcm.encrypt(nonce, sqlite_bytes, associated_data=MAGIC)
    return MAGIC + salt + nonce + ciphertext_and_tag


def decrypt_sqlite_payload(encrypted_bytes: bytes, master_password: str) -> bytes:
    """Decrypt a container. Header failures and tag failures use distinct errors."""
    _require_strong_key(master_password)
    if len(encrypted_bytes) < MIN_ENVELOPE_LEN:
        raise CryptoFormatError("FILE_TRUNCATED", "Encrypted database is shorter than the 48-byte envelope")
    magic = encrypted_bytes[: len(MAGIC)]
    if magic != MAGIC:
        raise CryptoFormatError("MAGIC_MISMATCH", "Encrypted database magic is not FCP1")
    salt = encrypted_bytes[4:20]
    nonce = encrypted_bytes[20:32]
    ciphertext_and_tag = encrypted_bytes[32:]
    aesgcm = AESGCM(derive_key(master_password, salt))
    return aesgcm.decrypt(nonce, ciphertext_and_tag, associated_data=MAGIC)


def _require_strong_key(master_password: str) -> None:
    if not master_key_is_strong(master_password):
        raise PermissionError("Master key shorter than 32 bytes")


__all__ = [
    "CryptoFormatError",
    "InvalidTag",
    "MASTER_KEY_PATH",
    "decrypt_sqlite_payload",
    "derive_key",
    "encrypt_sqlite_payload",
    "encrypted_header_ok",
    "resolve_master_key",
    "save_master_passphrase",
    "stretch_master_passphrase",
    "write_master_key",
]
