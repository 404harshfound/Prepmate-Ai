"""Practice session endpoints (Phase 2).

Flow:
  1. GET  /v1/questions/next    — pick the next question for the user
  2. POST /v1/sessions          — start a practice session
  3. POST /v1/sessions/{id}/answers — submit an answer, get STAR feedback
  4. POST /v1/sessions/{id}/complete — mark session done
  5. GET  /v1/sessions          — list past sessions with scores
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field

from app.config import Settings
from app.db import Connection, fetch_one
from app.deps import AppSettings, CurrentUser, Db
from app.feedback import FeedbackError, get_feedback

router = APIRouter(prefix="/v1", tags=["practice"])

RoundType = Literal["hr", "behavioural", "technical", "aptitude"]


# ------------------------------------------------------------------ schemas


class QuestionOut(BaseModel):
    id: UUID
    round_type: str
    topic: str
    difficulty: int
    prompt: str


class SessionCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    round_type: RoundType


class SessionOut(BaseModel):
    id: UUID
    round_type: str
    status: str
    started_at: datetime
    completed_at: datetime | None
    answer_count: int = 0
    average_score: float | None = None


class AnswerCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question_id: UUID
    transcript: str = Field(min_length=1, max_length=8000)


class ImprovementOut(BaseModel):
    issue: str
    suggestion: str


class FeedbackOut(BaseModel):
    overall: str
    improvements: list[ImprovementOut]


class ScoresOut(BaseModel):
    structure: int
    relevance: int
    clarity: int
    depth: int
    overall: float


class AnswerOut(BaseModel):
    id: UUID
    question_id: UUID
    transcript: str
    feedback_status: str
    scores: ScoresOut | None = None
    feedback: FeedbackOut | None = None
    model: str | None = None
    created_at: datetime


class UsageOut(BaseModel):
    feedback_calls: int
    feedback_limit: int
    audio_seconds: int
    audio_seconds_limit: int


# ------------------------------------------------------------------ helpers


async def _check_quota(conn: Connection, user_id: UUID, settings: Settings) -> int:
    """Return current feedback_calls count, raise 429 if over limit."""
    row = await fetch_one(
        conn,
        "select feedback_calls from app.daily_usage"
        " where user_id = %s and usage_date = (now() at time zone 'utc')::date",
        [user_id],
    )
    current = row["feedback_calls"] if row else 0
    if current >= settings.daily_feedback_limit:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            f"Daily feedback limit reached ({settings.daily_feedback_limit}). Try again tomorrow.",
            headers={"Retry-After": "3600"},
        )
    return current


async def _increment_usage(conn: Connection, user_id: UUID) -> None:
    """Bump today's feedback_calls counter by 1 (upsert)."""
    await conn.execute(
        "insert into app.daily_usage (user_id, usage_date, feedback_calls)"
        " values (%s, (now() at time zone 'utc')::date, 1)"
        " on conflict (user_id, usage_date)"
        " do update set feedback_calls = app.daily_usage.feedback_calls + 1",
        [user_id],
    )


# ------------------------------------------------------------------ endpoints


@router.get("/questions/next")
async def next_question(
    user: CurrentUser,
    db: Db,
    round_type: RoundType | None = None,
) -> QuestionOut:
    """Pick a question the user hasn't answered recently, or a random one."""
    filters = ["q.is_active"]
    params: list[object] = []
    if round_type:
        filters.append("q.round_type = %s")
        params.append(round_type)

    where = " and ".join(filters)

    # Prefer questions the user hasn't answered yet; fall back to least-recently
    # answered; finally fall back to random from the full active pool.
    query = f"""
        select q.id, q.round_type, q.topic, q.difficulty, q.prompt
        from app.questions q
        where {where}
          and q.id not in (
            select a.question_id from app.answers a where a.user_id = %s
          )
        order by random()
        limit 1
    """
    params.append(user.id)

    async with db.as_service() as conn:
        row = await fetch_one(conn, query, params)
        if row is None:
            # All questions answered — pick the least-recently answered one
            fallback = f"""
                select q.id, q.round_type, q.topic, q.difficulty, q.prompt
                from app.questions q
                left join (
                    select question_id, max(created_at) as last_answered
                    from app.answers where user_id = %s
                    group by question_id
                ) a on a.question_id = q.id
                where {" and ".join(filters)}
                order by a.last_answered asc nulls first
                limit 1
            """
            fallback_params: list[object] = [user.id]
            if round_type:
                fallback_params.append(round_type)
            row = await fetch_one(conn, fallback, fallback_params)
        if row is None:
            raise HTTPException(
                status.HTTP_404_NOT_FOUND,
                "No questions available" + (f" for round type '{round_type}'" if round_type else "") + ".",
            )
    return QuestionOut.model_validate(row)


@router.post("/sessions", status_code=status.HTTP_201_CREATED)
async def create_session(body: SessionCreate, user: CurrentUser, db: Db) -> SessionOut:
    """Start a new practice session."""
    async with db.as_service() as conn:
        row = await fetch_one(
            conn,
            "insert into app.practice_sessions (user_id, round_type)"
            " values (%s, %s) returning id, round_type, status, started_at, completed_at",
            [user.id, body.round_type],
        )
    assert row is not None
    return SessionOut(
        id=row["id"],
        round_type=row["round_type"],
        status=row["status"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
    )


@router.post("/sessions/{session_id}/answers", status_code=status.HTTP_201_CREATED)
async def submit_answer(
    session_id: UUID, body: AnswerCreate, user: CurrentUser, db: Db, settings: AppSettings
) -> AnswerOut:
    """Submit an answer and receive STAR feedback."""

    # Validate session belongs to user and is in progress
    async with db.as_service() as conn:
        session = await fetch_one(
            conn,
            "select id, user_id, status, round_type from app.practice_sessions where id = %s",
            [session_id],
        )
    if session is None or session["user_id"] != user.id:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found.")
    if session["status"] != "in_progress":
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            "This session is already completed.",
        )

    # Validate question exists
    async with db.as_service() as conn:
        question = await fetch_one(
            conn,
            "select id, prompt, round_type from app.questions where id = %s and is_active",
            [body.question_id],
        )
    if question is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Question not found.")

    # Check daily quota (as service — quota table is API-only)
    async with db.as_service() as conn:
        await _check_quota(conn, user.id, settings)

    # Get LLM feedback
    feedback_status = "pending"
    scores_dict = None
    feedback_dict = None
    model_used = None

    try:
        result = await get_feedback(
            question=question["prompt"],
            answer=body.transcript,
            round_type=question["round_type"],
            groq_api_key=settings.groq_api_key.get_secret_value() if settings.groq_api_key else None,
            groq_model=settings.groq_model,
            gemini_api_key=settings.gemini_api_key.get_secret_value() if settings.gemini_api_key else None,
            gemini_model=settings.gemini_model,
        )
        scores_dict = result.scores_dict()
        feedback_dict = result.feedback_dict()
        model_used = result.model
        feedback_status = "ready"
    except FeedbackError:
        feedback_status = "failed"

    # Insert answer and bump usage in one transaction
    async with db.as_service() as conn:
        row = await fetch_one(
            conn,
            "insert into app.answers"
            " (session_id, user_id, question_id, input_mode, transcript,"
            "  feedback_status, scores, feedback, model)"
            " values (%s, %s, %s, 'text', %s, %s, %s::jsonb, %s::jsonb, %s)"
            " returning id, question_id, transcript, feedback_status,"
            "          scores, feedback, model, created_at",
            [
                session_id,
                user.id,
                body.question_id,
                body.transcript,
                feedback_status,
                _json_or_none(scores_dict),
                _json_or_none(feedback_dict),
                model_used,
            ],
        )
        if feedback_status == "ready":
            await _increment_usage(conn, user.id)
    assert row is not None
    return _answer_from_row(row)


@router.post("/sessions/{session_id}/complete")
async def complete_session(session_id: UUID, user: CurrentUser, db: Db) -> SessionOut:
    """Mark a session as completed."""
    async with db.as_service() as conn:
        row = await fetch_one(
            conn,
            "update app.practice_sessions"
            " set status = 'completed', completed_at = now()"
            " where id = %s and user_id = %s and status = 'in_progress'"
            " returning id, round_type, status, started_at, completed_at",
            [session_id, user.id],
        )
    if row is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Session not found or already completed.")

    async with db.as_service() as conn:
        stats = await fetch_one(
            conn,
            "select count(*) as cnt,"
            " avg((scores->>'overall')::numeric) as avg_score"
            " from app.answers where session_id = %s and feedback_status = 'ready'",
            [session_id],
        )

    return SessionOut(
        id=row["id"],
        round_type=row["round_type"],
        status=row["status"],
        started_at=row["started_at"],
        completed_at=row["completed_at"],
        answer_count=stats["cnt"] if stats else 0,
        average_score=round(float(stats["avg_score"]), 1) if stats and stats["avg_score"] else None,
    )


@router.get("/sessions")
async def list_sessions(user: CurrentUser, db: Db) -> list[SessionOut]:
    """List the user's past sessions, newest first."""
    async with db.as_user(user) as conn:
        cursor = await conn.execute(
            "select s.id, s.round_type, s.status, s.started_at, s.completed_at,"
            " (select count(*) from app.answers a where a.session_id = s.id) as answer_count,"
            " (select avg((a.scores->>'overall')::numeric)"
            "  from app.answers a where a.session_id = s.id and a.feedback_status = 'ready') as average_score"
            " from app.practice_sessions s"
            " where s.user_id = (select auth.uid())"
            " order by s.started_at desc"
            " limit 50"
        )
        rows = await cursor.fetchall()
    return [
        SessionOut(
            id=r["id"],
            round_type=r["round_type"],
            status=r["status"],
            started_at=r["started_at"],
            completed_at=r["completed_at"],
            answer_count=r["answer_count"],
            average_score=round(float(r["average_score"]), 1) if r["average_score"] else None,
        )
        for r in rows
    ]


@router.get("/usage")
async def read_usage(user: CurrentUser, db: Db, settings: AppSettings) -> UsageOut:
    """Current daily usage for the signed-in user."""
    async with db.as_service() as conn:
        row = await fetch_one(
            conn,
            "select feedback_calls, audio_seconds from app.daily_usage"
            " where user_id = %s and usage_date = (now() at time zone 'utc')::date",
            [user.id],
        )
    return UsageOut(
        feedback_calls=row["feedback_calls"] if row else 0,
        feedback_limit=settings.daily_feedback_limit,
        audio_seconds=row["audio_seconds"] if row else 0,
        audio_seconds_limit=settings.daily_audio_seconds_limit,
    )


# ------------------------------------------------------------------ internal


import json as _json


def _json_or_none(value: dict | None) -> str | None:
    return _json.dumps(value) if value is not None else None


def _answer_from_row(row: dict) -> AnswerOut:
    scores = None
    feedback = None
    if row["scores"]:
        s = row["scores"] if isinstance(row["scores"], dict) else _json.loads(row["scores"])
        scores = ScoresOut(**s)
    if row["feedback"]:
        f = row["feedback"] if isinstance(row["feedback"], dict) else _json.loads(row["feedback"])
        feedback = FeedbackOut(
            overall=f["overall"],
            improvements=[ImprovementOut(**imp) for imp in f.get("improvements", [])],
        )
    return AnswerOut(
        id=row["id"],
        question_id=row["question_id"],
        transcript=row["transcript"],
        feedback_status=row["feedback_status"],
        scores=scores,
        feedback=feedback,
        model=row["model"],
        created_at=row["created_at"],
    )
