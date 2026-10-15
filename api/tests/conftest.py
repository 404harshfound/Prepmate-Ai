"""Shared test fixtures.

Database tests run the real migration files against a throwaway Postgres
database, so what we test is exactly what we deploy. Point
TEST_DATABASE_ADMIN_URL at any Postgres you can create databases on
(CI uses a service container; locally the default below works).
"""

import os
import time
import uuid
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import jwt
import psycopg
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from psycopg import sql

from app.auth import TokenVerifier

REPO_ROOT = Path(__file__).resolve().parents[2]
STUB = REPO_ROOT / "supabase" / "tests" / "local_supabase_stub.sql"
MIGRATIONS = sorted((REPO_ROOT / "supabase" / "migrations").glob("*.sql"))

ADMIN_URL = os.environ.get(
    "TEST_DATABASE_ADMIN_URL", "postgresql://postgres:postgres@localhost:5432/postgres"
)
API_ROLE_PASSWORD = "test-only-password"  # the throwaway test database only

ISSUER = "https://test-project.supabase.co/auth/v1"
AUDIENCE = "authenticated"
KID = "test-key-1"


# ---------------------------------------------------------------- tokens


class TokenFactory:
    """Signs tokens the way Supabase does, with a key only the tests know."""

    def __init__(self) -> None:
        self.private_key = ec.generate_private_key(ec.SECP256R1())
        public_jwk: dict[str, Any] = jwt.algorithms.ECAlgorithm.to_jwk(
            self.private_key.public_key(), as_dict=True
        )
        public_jwk.update({"kid": KID, "alg": "ES256", "use": "sig"})
        self.jwks: dict[str, Any] = {"keys": [public_jwk]}
        self.fetch_count = 0

    def fetch(self) -> dict[str, Any]:
        self.fetch_count += 1
        return self.jwks

    def claims(self, user_id: uuid.UUID, **overrides: Any) -> dict[str, Any]:
        now = int(time.time())
        claims: dict[str, Any] = {
            "iss": ISSUER,
            "aud": AUDIENCE,
            "sub": str(user_id),
            "role": "authenticated",
            "email": f"{str(user_id)[:8]}@example.com",
            "iat": now,
            "exp": now + 3600,
            "is_anonymous": False,
            "user_metadata": {"full_name": "Test User"},
        }
        claims.update(overrides)
        return {key: value for key, value in claims.items() if value is not None}

    def token(self, user_id: uuid.UUID, *, kid: str = KID, **overrides: Any) -> str:
        return jwt.encode(
            self.claims(user_id, **overrides),
            self.private_key,
            algorithm="ES256",
            headers={"kid": kid},
        )

    def verifier(self) -> TokenVerifier:
        return TokenVerifier(issuer=ISSUER, audience=AUDIENCE, fetch_jwks=self.fetch)


@pytest.fixture
def tokens() -> TokenFactory:
    return TokenFactory()


# ---------------------------------------------------------------- database


def _url_for(database: str, *, user: str, password: str) -> str:
    info = psycopg.conninfo.conninfo_to_dict(ADMIN_URL)
    info.update(dbname=database, user=user, password=password)
    return psycopg.conninfo.make_conninfo(**info)


@pytest.fixture(scope="session")
def migrated_database() -> Iterator[dict[str, str]]:
    """A fresh database with the stub and every migration applied."""
    name = f"prepmate_test_{uuid.uuid4().hex[:10]}"
    try:
        admin = psycopg.connect(ADMIN_URL, autocommit=True)
    except psycopg.OperationalError as exc:
        pytest.skip(f"No test Postgres available: {exc}")

    with admin:
        admin.execute(sql.SQL("create database {}").format(sql.Identifier(name)))
    admin_info = psycopg.conninfo.conninfo_to_dict(ADMIN_URL)
    admin_url = _url_for(
        name,
        user=str(admin_info.get("user", "postgres")),
        password=str(admin_info.get("password", "")),
    )
    try:
        with psycopg.connect(admin_url, autocommit=True) as conn:
            for path in [STUB, *MIGRATIONS]:
                conn.execute(path.read_text())  # type: ignore[arg-type]
            # In production this is set by hand, never from a file in git.
            conn.execute(
                sql.SQL("alter role prepmate_api login password {}").format(
                    sql.Literal(API_ROLE_PASSWORD)
                )
            )
        yield {
            "admin_url": admin_url,
            "api_url": _url_for(name, user="prepmate_api", password=API_ROLE_PASSWORD),
        }
    finally:
        with psycopg.connect(ADMIN_URL, autocommit=True) as conn:
            conn.execute(
                sql.SQL("drop database if exists {} with (force)").format(sql.Identifier(name))
            )


@pytest.fixture
def make_user(migrated_database: dict[str, str]) -> Iterator[Any]:
    """Creates rows in auth.users, as Supabase Auth would on sign-up."""
    created: list[uuid.UUID] = []

    def _make() -> uuid.UUID:
        user_id = uuid.uuid4()
        with psycopg.connect(migrated_database["admin_url"], autocommit=True) as conn:
            conn.execute(
                "insert into auth.users (id, email) values (%s, %s)",
                [user_id, f"{user_id.hex[:8]}@example.com"],
            )
        created.append(user_id)
        return user_id

    yield _make

    with psycopg.connect(migrated_database["admin_url"], autocommit=True) as conn:
        for user_id in created:
            conn.execute("delete from auth.users where id = %s", [user_id])
