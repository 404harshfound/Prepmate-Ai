from datetime import datetime
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, HTTPException, status
from psycopg import sql
from pydantic import BaseModel, ConfigDict, StringConstraints

from app.db import Connection, fetch_one
from app.deps import CurrentUser, Db

router = APIRouter(prefix="/v1", tags=["me"])

ExperienceLevel = Literal["student", "fresher", "experienced"]
ShortText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=80)]

# The only columns a user may write. Must match the column grants in the schema.
EDITABLE_COLUMNS = ("display_name", "target_role", "experience_level")


class Profile(BaseModel):
    display_name: str | None
    target_role: str | None
    experience_level: ExperienceLevel
    created_at: datetime


class Me(BaseModel):
    id: UUID
    email: str | None
    profile: Profile


class ProfileUpdate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    display_name: ShortText | None = None
    target_role: ShortText | None = None
    experience_level: ExperienceLevel | None = None


_SELECT_PROFILE = (
    "select display_name, target_role, experience_level, created_at"
    " from app.profiles where user_id = (select auth.uid())"
)


async def _load_profile(conn: Connection) -> Profile:
    row = await fetch_one(conn, _SELECT_PROFILE)
    if row is None:  # cannot happen after the insert below, but never assume
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Profile could not be loaded.")
    return Profile.model_validate(row)


@router.get("/me")
async def read_me(user: CurrentUser, db: Db) -> Me:
    """Who am I? Creates the profile row the first time a user shows up."""
    async with db.as_user(user) as conn:
        await conn.execute(
            "insert into app.profiles (user_id, display_name)"
            " values ((select auth.uid()), %s) on conflict (user_id) do nothing",
            [user.full_name],
        )
        profile = await _load_profile(conn)
    return Me(id=user.id, email=user.email, profile=profile)


@router.patch("/me")
async def update_me(changes: ProfileUpdate, user: CurrentUser, db: Db) -> Me:
    fields = {
        name: getattr(changes, name)
        for name in EDITABLE_COLUMNS
        if name in changes.model_fields_set and getattr(changes, name) is not None
    }
    if not fields:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "Nothing to update.")

    assignments = sql.SQL(", ").join(
        sql.SQL("{} = {}").format(sql.Identifier(name), sql.Placeholder()) for name in fields
    )
    query = sql.SQL("update app.profiles set {} where user_id = (select auth.uid())").format(
        assignments
    )
    async with db.as_user(user) as conn:
        cursor = await conn.execute(query, list(fields.values()))
        if cursor.rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Profile not found.")
        profile = await _load_profile(conn)
    return Me(id=user.id, email=user.email, profile=profile)
