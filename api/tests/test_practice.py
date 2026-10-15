"""Practice flow (Phase 2) end-to-end tests.

These test the question picker, session lifecycle, answer submission,
quota enforcement, and the feedback pipeline (with a mock LLM).
"""

import json
import uuid
from collections.abc import Iterator
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.config import Settings
from app.feedback import FeedbackError, FeedbackResult, Improvement, ScoreSet
from app.main import create_app
from tests.conftest import TokenFactory

ALLOWED_ORIGIN = "http://localhost:5173"

# A canned feedback result used by the mock
MOCK_FEEDBACK = FeedbackResult(
    scores=ScoreSet(structure=7, relevance=8, clarity=6, depth=7),
    overall="Good answer with clear STAR structure. Could add more quantitative results.",
    improvements=[
        Improvement(issue="Lacks metrics", suggestion="Add a percentage or number to the Result."),
    ],
    model="groq/test-model",
)


@pytest.fixture
def client(migrated_database: dict[str, str], tokens: TokenFactory) -> Iterator[TestClient]:
    settings = Settings(
        environment="test",
        supabase_url="https://test-project.supabase.co",
        database_url=SecretStr(migrated_database["api_url"]),
        cors_origins=[ALLOWED_ORIGIN],
        groq_api_key=SecretStr("test-groq-key"),
    )
    app = create_app(settings, verifier=tokens.verifier())
    with TestClient(app) as tc:
        yield tc


def auth(tokens: TokenFactory, user_id: uuid.UUID) -> dict[str, str]:
    return {"Authorization": f"Bearer {tokens.token(user_id)}"}


# ------------------------------------------------------------------ questions


def test_next_question_returns_a_question(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)  # ensure profile exists

    response = client.get("/v1/questions/next", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert "id" in body
    assert "prompt" in body
    assert body["round_type"] in ("hr", "behavioural", "technical", "aptitude")
    assert body["difficulty"] in (1, 2, 3)


def test_next_question_filtered_by_round_type(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    response = client.get("/v1/questions/next?round_type=technical", headers=headers)
    assert response.status_code == 200
    assert response.json()["round_type"] == "technical"


def test_next_question_rejects_bad_round_type(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    response = client.get("/v1/questions/next?round_type=magic", headers=headers)
    assert response.status_code == 422


# ------------------------------------------------------------------ sessions


def test_create_session(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    response = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"})
    assert response.status_code == 201
    body = response.json()
    assert body["round_type"] == "hr"
    assert body["status"] == "in_progress"
    assert body["completed_at"] is None


def test_complete_session(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    session = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"}).json()
    response = client.post(f"/v1/sessions/{session['id']}/complete", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "completed"
    assert response.json()["completed_at"] is not None


def test_complete_other_users_session_is_404(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    alice, bob = make_user(), make_user()
    client.get("/v1/me", headers=auth(tokens, alice))
    client.get("/v1/me", headers=auth(tokens, bob))

    session = client.post(
        "/v1/sessions", headers=auth(tokens, alice), json={"round_type": "hr"}
    ).json()
    response = client.post(
        f"/v1/sessions/{session['id']}/complete", headers=auth(tokens, bob)
    )
    assert response.status_code == 404


def test_list_sessions(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    client.post("/v1/sessions", headers=headers, json={"round_type": "hr"})
    client.post("/v1/sessions", headers=headers, json={"round_type": "technical"})

    response = client.get("/v1/sessions", headers=headers)
    assert response.status_code == 200
    sessions = response.json()
    assert len(sessions) >= 2
    # Newest first
    assert sessions[0]["round_type"] in ("hr", "technical")


# ------------------------------------------------------------------ answers


@patch("app.routers.practice.get_feedback", new_callable=AsyncMock)
def test_submit_answer_with_feedback(
    mock_feedback: AsyncMock,
    client: TestClient,
    tokens: TokenFactory,
    make_user,
) -> None:
    mock_feedback.return_value = MOCK_FEEDBACK
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    # Create session and get a question
    session = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"}).json()
    question = client.get("/v1/questions/next?round_type=hr", headers=headers).json()

    # Submit answer
    response = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=headers,
        json={"question_id": question["id"], "transcript": "I have experience with Python and React."},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["feedback_status"] == "ready"
    assert body["scores"]["structure"] == 7
    assert body["scores"]["overall"] == 7.0
    assert body["feedback"]["overall"].startswith("Good answer")
    assert len(body["feedback"]["improvements"]) == 1
    assert body["model"] == "groq/test-model"
    mock_feedback.assert_called_once()


@patch("app.routers.practice.get_feedback", new_callable=AsyncMock)
def test_submit_answer_feedback_failure_still_saves(
    mock_feedback: AsyncMock,
    client: TestClient,
    tokens: TokenFactory,
    make_user,
) -> None:
    mock_feedback.side_effect = FeedbackError("All providers failed")
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    session = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"}).json()
    question = client.get("/v1/questions/next?round_type=hr", headers=headers).json()

    response = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=headers,
        json={"question_id": question["id"], "transcript": "Some answer here."},
    )
    assert response.status_code == 201
    body = response.json()
    assert body["feedback_status"] == "failed"
    assert body["scores"] is None
    assert body["feedback"] is None


def test_submit_answer_to_completed_session_fails(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    session = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"}).json()
    client.post(f"/v1/sessions/{session['id']}/complete", headers=headers)

    question = client.get("/v1/questions/next?round_type=hr", headers=headers).json()
    response = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=headers,
        json={"question_id": question["id"], "transcript": "Too late."},
    )
    assert response.status_code == 422


def test_submit_answer_empty_transcript_rejected(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    session = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"}).json()
    question = client.get("/v1/questions/next?round_type=hr", headers=headers).json()

    response = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=headers,
        json={"question_id": question["id"], "transcript": ""},
    )
    assert response.status_code == 422


def test_submit_answer_to_other_users_session_is_404(
    client: TestClient, tokens: TokenFactory, make_user
) -> None:
    alice, bob = make_user(), make_user()
    client.get("/v1/me", headers=auth(tokens, alice))
    client.get("/v1/me", headers=auth(tokens, bob))

    session = client.post(
        "/v1/sessions", headers=auth(tokens, alice), json={"round_type": "hr"}
    ).json()
    question = client.get("/v1/questions/next?round_type=hr", headers=auth(tokens, bob)).json()

    response = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=auth(tokens, bob),
        json={"question_id": question["id"], "transcript": "Hacking attempt."},
    )
    assert response.status_code == 404


# ------------------------------------------------------------------ quota


@patch("app.routers.practice.get_feedback", new_callable=AsyncMock)
def test_daily_quota_enforcement(
    mock_feedback: AsyncMock,
    client: TestClient,
    tokens: TokenFactory,
    make_user,
    migrated_database: dict[str, str],
) -> None:
    """After hitting the daily limit, the next answer returns 429."""
    import psycopg

    mock_feedback.return_value = MOCK_FEEDBACK
    user_id = make_user()
    headers = auth(tokens, user_id)
    client.get("/v1/me", headers=headers)

    # Manually set the usage counter to limit - 1
    with psycopg.connect(migrated_database["admin_url"], autocommit=True) as conn:
        conn.execute(
            "insert into app.daily_usage (user_id, usage_date, feedback_calls)"
            " values (%s, (now() at time zone 'utc')::date, 19)",
            [user_id],
        )

    session = client.post("/v1/sessions", headers=headers, json={"round_type": "hr"}).json()
    question = client.get("/v1/questions/next?round_type=hr", headers=headers).json()

    # This one should succeed (call 20 = limit)
    r1 = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=headers,
        json={"question_id": question["id"], "transcript": "Answer at the limit."},
    )
    assert r1.status_code == 201

    # Next one should be rate limited
    question2 = client.get("/v1/questions/next?round_type=hr", headers=headers).json()
    r2 = client.post(
        f"/v1/sessions/{session['id']}/answers",
        headers=headers,
        json={"question_id": question2["id"], "transcript": "Over the limit."},
    )
    assert r2.status_code == 429
    assert "limit" in r2.json()["error"]["message"].lower()


# ------------------------------------------------------------------ usage


def test_usage_endpoint(client: TestClient, tokens: TokenFactory, make_user) -> None:
    user_id = make_user()
    headers = auth(tokens, user_id)

    response = client.get("/v1/usage", headers=headers)
    assert response.status_code == 200
    body = response.json()
    assert body["feedback_calls"] == 0
    assert body["feedback_limit"] == 20
    assert body["audio_seconds"] == 0


# ------------------------------------------------------------------ feedback parsing

def test_feedback_result_serialisation() -> None:
    """FeedbackResult round-trips through dict correctly."""
    scores = MOCK_FEEDBACK.scores_dict()
    assert scores["structure"] == 7
    assert scores["overall"] == 7.0

    feedback = MOCK_FEEDBACK.feedback_dict()
    assert "Good answer" in feedback["overall"]
    assert len(feedback["improvements"]) == 1

    # Ensure it's JSON-serialisable
    json.dumps(scores)
    json.dumps(feedback)


def test_parse_response_handles_markdown_fences() -> None:
    from app.feedback import _parse_response

    raw = '```json\n{"scores":{"structure":5,"relevance":6,"clarity":7,"depth":4},"overall":"Decent.","improvements":[]}\n```'
    result = _parse_response(raw, "test/model")
    assert result.scores.structure == 5
    assert result.overall == "Decent."
    assert result.model == "test/model"


def test_parse_response_clamps_scores() -> None:
    from app.feedback import _parse_response

    raw = json.dumps({
        "scores": {"structure": 15, "relevance": -2, "clarity": "bad", "depth": 7},
        "overall": "Test.",
        "improvements": [],
    })
    result = _parse_response(raw, "test/model")
    assert result.scores.structure == 10  # clamped from 15
    assert result.scores.relevance == 1   # clamped from -2
    assert result.scores.clarity == 5     # default for non-int
    assert result.scores.depth == 7
