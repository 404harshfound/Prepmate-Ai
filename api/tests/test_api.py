"""The HTTP API, end to end against a real migrated database."""

import uuid
from collections.abc import Iterator

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.main import create_app
from tests.conftest import TokenFactory

ALLOWED_ORIGIN = "http://localhost:5173"


@pytest.fixture
def client(migrated_database: dict[str, str], tokens: TokenFactory) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        supabase_url="https://test-project.supabase.co",
        database_url=SecretStr(migrated_database["api_url"]),
        cors_origins=[ALLOWED_ORIGIN],
    )
    app = create_app(settings, verifier=tokens.verifier())
    with TestClient(app) as test_client:
        yield test_client


def auth_header(tokens: TokenFactory, user_id: uuid.UUID, **claims: object) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens.token(user_id, **claims)}"}


def test_liveness_and_security_headers(client: TestClient) -> None:
    response = client.get("/healthz")
    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert "X-Request-ID" in response.headers


def test_readiness_checks_the_database(client: TestClient) -> None:
    assert client.get("/readyz").json() == {"status": "ok", "database": "ok"}


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer not-a-token"}, {"Authorization": "Basic dXNlcjpwYXNz"}],
)
def test_me_requires_a_valid_token(client: TestClient, headers: dict[str, str]) -> None:
    response = client.get("/v1/me", headers=headers)
    assert response.status_code == 401
    body = response.json()
    assert body["error"]["code"] == "unauthenticated"
    assert body["error"]["request_id"]
    assert response.headers["Cache-Control"] == "no-store"


def test_expired_token_is_rejected(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    headers = auth_header(tokens, user_id, exp=1, iat=0)
    assert client.get("/v1/me", headers=headers).status_code == 401


def test_first_visit_creates_profile(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    response = client.get("/v1/me", headers=auth_header(tokens, user_id))
    assert response.status_code == 200
    body = response.json()
    assert body["id"] == str(user_id)
    assert body["profile"]["display_name"] == "Test User"
    assert body["profile"]["experience_level"] == "student"

    # Second visit returns the same profile, no duplicate row.
    again = client.get("/v1/me", headers=auth_header(tokens, user_id)).json()
    assert again["profile"]["created_at"] == body["profile"]["created_at"]


def test_update_profile(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    headers = auth_header(tokens, user_id)
    client.get("/v1/me", headers=headers)
    response = client.patch(
        "/v1/me",
        headers=headers,
        json={"target_role": "  Backend SDE  ", "experience_level": "fresher"},
    )
    assert response.status_code == 200
    profile = response.json()["profile"]
    assert profile["target_role"] == "Backend SDE"  # trimmed
    assert profile["experience_level"] == "fresher"
    assert profile["display_name"] == "Test User"  # untouched


@pytest.mark.parametrize(
    "body",
    [
        {},  # nothing to change
        {"user_id": str(uuid.uuid4())},  # not an editable field
        {"display_name": "x" * 81},  # too long
        {"display_name": "   "},  # blank
        {"experience_level": "ceo"},  # not an allowed value
    ],
)
def test_update_rejects_bad_input(
    client: TestClient, tokens: TokenFactory, make_user, body
) -> None:
    user_id = make_user()
    headers = auth_header(tokens, user_id)
    client.get("/v1/me", headers=headers)
    response = client.patch("/v1/me", headers=headers, json=body)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "invalid_request"


def test_users_are_isolated_through_the_api(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    alice, bob = make_user(), make_user()
    client.get("/v1/me", headers=auth_header(tokens, alice))
    client.patch("/v1/me", headers=auth_header(tokens, alice), json={"target_role": "Alice role"})

    bob_view = client.get("/v1/me", headers=auth_header(tokens, bob)).json()
    assert bob_view["id"] == str(bob)
    assert bob_view["profile"]["target_role"] is None


def test_token_for_deleted_user_cannot_create_profile(
    client: TestClient, tokens: TokenFactory
) -> None:
    ghost = uuid.uuid4()  # validly signed, but no such user in auth.users
    response = client.get("/v1/me", headers=auth_header(tokens, ghost))
    assert response.status_code == 500
    assert response.json()["error"]["code"] == "internal_error"
    assert "violates" not in response.text  # no database detail leaks out


def test_cors_allows_only_our_frontend(client: TestClient) -> None:
    allowed = client.options(
        "/v1/me",
        headers={"Origin": ALLOWED_ORIGIN, "Access-Control-Request-Method": "GET"},
    )
    assert allowed.headers.get("access-control-allow-origin") == ALLOWED_ORIGIN

    blocked = client.options(
        "/v1/me",
        headers={"Origin": "https://evil.example", "Access-Control-Request-Method": "GET"},
    )
    assert "access-control-allow-origin" not in blocked.headers


def test_production_settings_refuse_unsafe_cors() -> None:
    with pytest.raises(ValueError, match="Wildcard"):
        Settings(
            environment="production",
            supabase_url="https://x.supabase.co",
            database_url=SecretStr("postgresql://x"),
            cors_origins=["*"],
        )
    with pytest.raises(ValueError, match="https"):
        Settings(
            environment="production",
            supabase_url="https://x.supabase.co",
            database_url=SecretStr("postgresql://x"),
            cors_origins=["http://prepmate.example"],
        )


def test_docs_hidden_in_production(migrated_database: dict[str, str], tokens: TokenFactory) -> None:
    settings = Settings(
        environment="production",
        supabase_url="https://test-project.supabase.co",
        database_url=SecretStr(migrated_database["api_url"]),
        cors_origins=["https://prepmate.example"],
    )
    with TestClient(create_app(settings, verifier=tokens.verifier())) as prod:
        assert prod.get("/docs").status_code == 404
        assert prod.get("/openapi.json").status_code == 404
        headers = prod.get("/healthz").headers
        assert "max-age" in headers["Strict-Transport-Security"]
        assert headers["Content-Security-Policy"].startswith("default-src 'none'")
