"""Unit tests for core security primitives — no DB, no FastAPI involved."""

import time

import pytest

from app.core.security import create_access_token, decode_access_token, hash_password, verify_password


@pytest.mark.unit
def test_hash_password_produces_different_hash_each_time() -> None:
    """
    bcrypt salts each hash independently, so hashing the same password
    twice must NOT produce identical output — this is what prevents an
    attacker from spotting "these two users share a password" just by
    comparing hashes in a leaked database dump.
    """
    hash_one = hash_password("correct-horse-battery-staple")
    hash_two = hash_password("correct-horse-battery-staple")
    assert hash_one != hash_two


@pytest.mark.unit
def test_verify_password_accepts_correct_and_rejects_incorrect() -> None:
    hashed = hash_password("my-secure-password")
    assert verify_password("my-secure-password", hashed) is True
    assert verify_password("wrong-password", hashed) is False


@pytest.mark.unit
def test_access_token_round_trips_subject_and_claims() -> None:
    token = create_access_token(subject="user-123", extra_claims={"role": "recruiter"})
    payload = decode_access_token(token)

    assert payload is not None
    assert payload["sub"] == "user-123"
    assert payload["role"] == "recruiter"


@pytest.mark.unit
def test_decode_rejects_tampered_token() -> None:
    """A token with an altered signature must never decode successfully."""
    token = create_access_token(subject="user-123")
    tampered = token[:-4] + "abcd"  # corrupt the signature segment

    assert decode_access_token(tampered) is None


@pytest.mark.unit
def test_decode_rejects_garbage_input() -> None:
    assert decode_access_token("not-a-real-jwt-at-all") is None
