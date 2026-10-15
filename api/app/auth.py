"""Verifies Supabase access tokens.

The browser signs in with Supabase Auth and sends the access token as a
Bearer header. Supabase signs those tokens with a private key that never
leaves Supabase; we check the signature against the project's public keys
(the JWKS endpoint). The user id is taken from the verified token and from
nowhere else - never from a request body or query string.
"""

import json
import logging
import threading
import time
from collections.abc import Callable
from typing import Any
from uuid import UUID

import httpx
import jwt
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Asymmetric algorithms only. Accepting HS256 here would let anyone who knows
# the *public* key forge tokens (the "algorithm confusion" attack).
ALLOWED_ALGORITHMS = ("ES256", "RS256")

JWKS_TTL_SECONDS = 600  # Supabase caches the key set at its edge for 10 minutes
JWKS_MIN_REFRESH_SECONDS = 30  # unknown key ids can't make us hammer Supabase
JWKS_MAX_STALE_SECONDS = 3600  # keep working through a short Supabase Auth outage
CLOCK_SKEW_SECONDS = 10


class InvalidTokenError(Exception):
    """The token is missing, malformed, expired, or not signed by our project."""


class AuthUnavailableError(Exception):
    """We could not load the signing keys, so no token can be checked right now."""


class AuthUser(BaseModel):
    id: UUID
    email: str | None = None
    full_name: str | None = None

    @property
    def db_claims(self) -> str:
        """The minimal claims Postgres needs to apply row-level security."""
        return json.dumps({"sub": str(self.id), "role": "authenticated"})


JwksFetcher = Callable[[], dict[str, Any]]


def http_jwks_fetcher(url: str) -> JwksFetcher:
    def fetch() -> dict[str, Any]:
        response = httpx.get(url, timeout=5.0)
        response.raise_for_status()
        data: dict[str, Any] = response.json()
        return data

    return fetch


class TokenVerifier:
    def __init__(self, *, issuer: str, audience: str, fetch_jwks: JwksFetcher) -> None:
        self._issuer = issuer
        self._audience = audience
        self._fetch_jwks = fetch_jwks
        self._keys: dict[str, jwt.PyJWK] = {}
        self._fetched_at = 0.0
        self._attempted_at = 0.0
        self._lock = threading.Lock()

    def _refresh(self) -> None:
        self._attempted_at = time.monotonic()
        try:
            jwks = self._fetch_jwks()
            keys: dict[str, jwt.PyJWK] = {}
            for raw in jwks.get("keys", []):
                if raw.get("alg") not in ALLOWED_ALGORITHMS or "kid" not in raw:
                    continue
                keys[raw["kid"]] = jwt.PyJWK(raw)
        except Exception as exc:
            logger.warning("Could not refresh signing keys: %s", type(exc).__name__)
            return
        self._keys = keys
        self._fetched_at = time.monotonic()

    def _key_for(self, kid: str) -> jwt.PyJWK:
        with self._lock:
            now = time.monotonic()
            age = now - self._fetched_at
            since_attempt = now - self._attempted_at
            never_loaded = self._fetched_at == 0.0
            expired = never_loaded or age > JWKS_TTL_SECONDS
            unknown_kid = kid not in self._keys

            may_retry = never_loaded and self._attempted_at == 0.0
            may_retry = may_retry or since_attempt > JWKS_MIN_REFRESH_SECONDS
            if (expired or unknown_kid) and may_retry:
                self._refresh()

            usable = (
                self._fetched_at != 0.0
                and (time.monotonic() - self._fetched_at) <= JWKS_MAX_STALE_SECONDS
            )
            if not usable:
                raise AuthUnavailableError("signing keys unavailable")
            key = self._keys.get(kid)
            if key is None:
                raise InvalidTokenError("unknown signing key")
            return key

    def verify(self, token: str) -> AuthUser:
        try:
            header = jwt.get_unverified_header(token)
        except jwt.PyJWTError as exc:
            raise InvalidTokenError("malformed token") from exc

        algorithm = header.get("alg")
        kid = header.get("kid")
        if algorithm not in ALLOWED_ALGORITHMS or not isinstance(kid, str):
            raise InvalidTokenError("unsupported token")

        key = self._key_for(kid)
        if key.algorithm_name != algorithm:
            raise InvalidTokenError("algorithm does not match signing key")

        try:
            claims = jwt.decode(
                token,
                key,
                algorithms=[algorithm],
                audience=self._audience,
                issuer=self._issuer,
                leeway=CLOCK_SKEW_SECONDS,
                options={"require": ["exp", "iat", "sub", "aud", "iss"]},
            )
        except jwt.PyJWTError as exc:
            raise InvalidTokenError(type(exc).__name__) from exc

        if claims.get("role") != "authenticated" or claims.get("is_anonymous") is True:
            raise InvalidTokenError("not a signed-in user")

        try:
            user_id = UUID(str(claims["sub"]))
        except ValueError as exc:
            raise InvalidTokenError("subject is not a user id") from exc

        metadata = claims.get("user_metadata")
        full_name = None
        if isinstance(metadata, dict):
            candidate = metadata.get("full_name") or metadata.get("name")
            if isinstance(candidate, str) and candidate.strip():
                full_name = candidate.strip()[:80]

        email = claims.get("email")
        return AuthUser(
            id=user_id,
            email=email if isinstance(email, str) and email else None,
            full_name=full_name,
        )
