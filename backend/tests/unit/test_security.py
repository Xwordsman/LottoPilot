"""Unit tests for security helpers."""

from __future__ import annotations

from app.core.security import (
    decrypt_secret,
    encrypt_secret,
    generate_session_token,
    hash_password,
    hash_session_token,
    mask_secret,
    verify_password,
)


def test_password_hash_and_verify() -> None:
    hashed = hash_password("Secret123!")
    assert verify_password(hashed, "Secret123!")
    assert not verify_password(hashed, "wrong")


def test_session_token_hash_stable() -> None:
    token = generate_session_token()
    assert len(token) >= 32
    assert hash_session_token(token) == hash_session_token(token)
    assert len(hash_session_token(token)) == 64


def test_encrypt_decrypt_roundtrip() -> None:
    secret = "app-secret-key-for-tests-0123456789"
    cipher = encrypt_secret("sk-test-key", secret)
    assert decrypt_secret(cipher, secret) == "sk-test-key"
    assert mask_secret("sk-abcdefghij", visible=4).endswith("ghij")
