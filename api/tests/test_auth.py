"""Token verification: every way a forged or stale token could get in."""

import base64
import json
import time
import uuid
from typing import Any

import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ec

from app import auth
from app.auth import AuthUnavailableError, InvalidTokenError, TokenVerifier
from tests.conftest import AUDIENCE, ISSUER, KID, TokenFactory


def test_valid_token_returns_user(tokens: TokenFactory) -> None:
    user_id = uuid.uuid4()
    user = tokens.verifier().verify(tokens.token(user_id))
    assert user.id == user_id
    assert user.full_name == "Test User"
    assert user.email is not None


@pytest.mark.parametrize(
    "overrides",
    [
        {"exp": int(time.time()) - 60},  # expired
        {"iss": "https://someone-else.supabase.co/auth/v1"},  # another project
        {"aud": "service_role"},
        {"role": "anon"},
        {"role": "service_role"},
        {"is_anonymous": True},
        {"sub": "not-a-uuid"},
        {"exp": None},  # missing expiry
        {"sub": None},  # missing subject
    ],
)
def test_rejects_bad_claims(tokens: TokenFactory, overrides: dict[str, Any]) -> None:
    token = tokens.token(uuid.uuid4(), **overrides)
    with pytest.raises(InvalidTokenError):
        tokens.verifier().verify(token)


def test_rejects_token_signed_by_another_key(tokens: TokenFactory) -> None:
    attacker_key = ec.generate_private_key(ec.SECP256R1())
    token = jwt.encode(
        tokens.claims(uuid.uuid4()), attacker_key, algorithm="ES256", headers={"kid": KID}
    )
    with pytest.raises(InvalidTokenError):
        tokens.verifier().verify(token)


def test_rejects_algorithm_confusion(tokens: TokenFactory) -> None:
    """HS256 signed with the *public* key must never verify."""
    public_pem = tokens.private_key.public_key().public_bytes(
        serialization.Encoding.PEM, serialization.PublicFormat.SubjectPublicKeyInfo
    )

    def b64(data: bytes) -> str:
        return base64.urlsafe_b64encode(data).rstrip(b"=").decode()

    import hashlib
    import hmac

    header = b64(json.dumps({"alg": "HS256", "kid": KID, "typ": "JWT"}).encode())
    payload = b64(json.dumps(tokens.claims(uuid.uuid4())).encode())
    signature = hmac.new(public_pem, f"{header}.{payload}".encode(), hashlib.sha256).digest()
    forged = f"{header}.{payload}.{b64(signature)}"
    with pytest.raises(InvalidTokenError):
        tokens.verifier().verify(forged)


def test_rejects_unsigned_token(tokens: TokenFactory) -> None:
    token = jwt.encode(tokens.claims(uuid.uuid4()), key=None, algorithm="none")
    with pytest.raises(InvalidTokenError):
        tokens.verifier().verify(token)


@pytest.mark.parametrize("token", ["", "garbage", "a.b.c", "Bearer x"])
def test_rejects_malformed_token(tokens: TokenFactory, token: str) -> None:
    with pytest.raises(InvalidTokenError):
        tokens.verifier().verify(token)


def test_unknown_key_ids_cannot_hammer_supabase(tokens: TokenFactory) -> None:
    verifier = tokens.verifier()
    verifier.verify(tokens.token(uuid.uuid4()))
    assert tokens.fetch_count == 1
    for _ in range(20):
        with pytest.raises(InvalidTokenError):
            verifier.verify(tokens.token(uuid.uuid4(), kid="unknown-kid"))
    assert tokens.fetch_count == 1  # refresh is rate-limited


def test_keys_unavailable_is_not_reported_as_bad_token() -> None:
    def failing_fetch() -> dict[str, Any]:
        raise ConnectionError("supabase down")

    factory = TokenFactory()
    verifier = TokenVerifier(issuer=ISSUER, audience=AUDIENCE, fetch_jwks=failing_fetch)
    with pytest.raises(AuthUnavailableError):
        verifier.verify(factory.token(uuid.uuid4()))


def test_survives_short_auth_outage(tokens: TokenFactory, monkeypatch: pytest.MonkeyPatch) -> None:
    clock = [1000.0]
    monkeypatch.setattr(auth.time, "monotonic", lambda: clock[0])
    calls = {"fail": False}

    def flaky_fetch() -> dict[str, Any]:
        if calls["fail"]:
            raise ConnectionError("supabase down")
        return tokens.jwks

    verifier = TokenVerifier(issuer=ISSUER, audience=AUDIENCE, fetch_jwks=flaky_fetch)
    verifier.verify(tokens.token(uuid.uuid4()))

    calls["fail"] = True
    clock[0] += auth.JWKS_TTL_SECONDS + 1  # keys are due a refresh, which fails
    verifier.verify(tokens.token(uuid.uuid4()))  # cached keys still accepted

    clock[0] += auth.JWKS_MAX_STALE_SECONDS  # far too stale now
    with pytest.raises(AuthUnavailableError):
        verifier.verify(tokens.token(uuid.uuid4()))
