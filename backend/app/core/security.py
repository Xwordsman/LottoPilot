"""Security helpers: password hashing, tokens, encryption placeholders."""

from __future__ import annotations

from base64 import urlsafe_b64encode
import hashlib
import hmac
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

_password_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _password_hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    try:
        return _password_hasher.verify(password_hash, password)
    except VerifyMismatchError:
        return False


def generate_session_token() -> str:
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def constant_time_equals(left: str, right: str) -> bool:
    return hmac.compare_digest(left, right)


def derive_fernet_key(secret: str) -> bytes:
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=b"lottopilot-ai-key-v1",
        info=b"ai-config-key",
    )
    material = hkdf.derive(secret.encode("utf-8"))
    return urlsafe_b64encode(material)


def encrypt_secret(plaintext: str, app_secret: str) -> str:
    fernet = Fernet(derive_fernet_key(app_secret))
    return fernet.encrypt(plaintext.encode("utf-8")).decode("utf-8")


def decrypt_secret(ciphertext: str, app_secret: str) -> str:
    fernet = Fernet(derive_fernet_key(app_secret))
    try:
        return fernet.decrypt(ciphertext.encode("utf-8")).decode("utf-8")
    except InvalidToken as exc:
        raise ValueError("failed to decrypt secret") from exc


def mask_secret(value: str, visible: int = 4) -> str:
    if not value:
        return ""
    if len(value) <= visible:
        return "*" * len(value)
    return f"{'*' * max(4, len(value) - visible)}{value[-visible:]}"
