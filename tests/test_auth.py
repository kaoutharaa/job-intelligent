"""
Unit tests for the API's security primitives — password hashing and JWT tokens.

These are pure functions with no database dependency, so they run without a
live Postgres. Run with:  pytest -q
"""
import time

import jwt
import pytest

from api.api import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
    JWT_SECRET,
    JWT_ALGORITHM,
)


# ─── PASSWORD HASHING ────────────────────────────────────────────────────────────

def test_hash_password_roundtrip():
    hashed = hash_password("correct horse battery staple")
    assert verify_password("correct horse battery staple", hashed)


def test_hash_password_rejects_wrong_password():
    hashed = hash_password("s3cret-pass")
    assert not verify_password("wrong-pass", hashed)


def test_hash_password_is_salted():
    # Same input hashed twice must differ (random per-password salt).
    assert hash_password("same") != hash_password("same")


def test_verify_password_handles_malformed_hash():
    # Must not raise on garbage input — just return False.
    assert not verify_password("whatever", "not-a-valid-hash")
    assert not verify_password("whatever", "")


# ─── JWT TOKENS ──────────────────────────────────────────────────────────────────

def test_token_roundtrip():
    token = create_access_token(42)
    assert decode_access_token(token) == 42


def test_decode_rejects_tampered_token():
    token = create_access_token(1)
    tampered = token[:-2] + ("aa" if not token.endswith("aa") else "bb")
    with pytest.raises(Exception):
        decode_access_token(tampered)


def test_decode_rejects_foreign_secret():
    forged = jwt.encode({"sub": "999"}, "attacker-secret", algorithm=JWT_ALGORITHM)
    with pytest.raises(Exception):
        decode_access_token(forged)


def test_decode_rejects_expired_token():
    now = int(time.time())
    expired = jwt.encode(
        {"sub": "7", "iat": now - 100, "exp": now - 10},
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )
    with pytest.raises(Exception):
        decode_access_token(expired)
