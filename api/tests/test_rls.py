"""Row-level security, tested directly in Postgres.

These run as the same login role the API uses, so they prove the database
itself keeps users apart, even if a bug in our Python forgot a WHERE clause.
"""

import json
import uuid
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
import pytest
from psycopg import errors

pytestmark = pytest.mark.usefixtures("migrated_database")


@contextmanager
def as_user(api_url: str, user_id: uuid.UUID) -> Iterator[psycopg.Connection]:
    with psycopg.connect(api_url) as conn, conn.transaction():
        claims = json.dumps({"sub": str(user_id), "role": "authenticated"})
        conn.execute("select set_config('request.jwt.claims', %s, true)", [claims])
        conn.execute("set local role authenticated")
        yield conn


def _seed(admin_url: str, owner: uuid.UUID) -> uuid.UUID:
    """A profile, a session and an answer belonging to `owner`. Returns the session id."""
    with psycopg.connect(admin_url, autocommit=True) as conn:
        conn.execute(
            "insert into app.profiles (user_id, display_name) values (%s, 'Owner')", [owner]
        )
        question = conn.execute(
            "insert into app.questions (round_type, topic, difficulty, prompt, reference_answer)"
            " values ('hr', 'intro', 1, 'Tell me about yourself.', 'A short, structured intro.')"
            " returning id"
        ).fetchone()
        session = conn.execute(
            "insert into app.practice_sessions (user_id, round_type)"
            " values (%s, 'hr') returning id",
            [owner],
        ).fetchone()
        assert question and session
        conn.execute(
            "insert into app.answers (session_id, user_id, question_id, transcript)"
            " values (%s, %s, %s, 'My answer')",
            [session[0], owner, question[0]],
        )
        conn.execute("insert into app.daily_usage (user_id) values (%s)", [owner])
        return uuid.UUID(str(session[0]))


@pytest.fixture
def two_users(make_user, migrated_database):
    alice, bob = make_user(), make_user()
    _seed(migrated_database["admin_url"], alice)
    return alice, bob


@pytest.mark.parametrize("table", ["profiles", "practice_sessions", "answers", "daily_usage"])
def test_users_see_only_their_own_rows(two_users, migrated_database, table) -> None:
    alice, bob = two_users
    query = f"select count(*) from app.{table}"
    with as_user(migrated_database["api_url"], alice) as conn:
        assert conn.execute(query).fetchone() == (1,)
    with as_user(migrated_database["api_url"], bob) as conn:
        assert conn.execute(query).fetchone() == (0,)


def test_users_cannot_read_the_question_bank(two_users, migrated_database) -> None:
    alice, _ = two_users
    with (
        as_user(migrated_database["api_url"], alice) as conn,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        conn.execute("select reference_answer from app.questions")


def test_users_cannot_write_their_own_scores(two_users, migrated_database) -> None:
    alice, _ = two_users
    with (
        as_user(migrated_database["api_url"], alice) as conn,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        conn.execute("update app.answers set scores = '{\"overall\": 10}'")


def test_users_cannot_reset_their_quota(two_users, migrated_database) -> None:
    alice, _ = two_users
    with (
        as_user(migrated_database["api_url"], alice) as conn,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        conn.execute("update app.daily_usage set feedback_calls = 0")


def test_users_cannot_change_profile_owner(two_users, migrated_database) -> None:
    alice, bob = two_users
    with (
        as_user(migrated_database["api_url"], alice) as conn,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        conn.execute("update app.profiles set user_id = %s", [bob])


def test_users_cannot_edit_someone_elses_profile(two_users, migrated_database) -> None:
    alice, bob = two_users
    with as_user(migrated_database["api_url"], bob) as conn:
        cursor = conn.execute(
            "update app.profiles set display_name = 'hacked' where user_id = %s", [alice]
        )
        assert cursor.rowcount == 0


def test_users_cannot_create_a_profile_for_someone_else(two_users, migrated_database) -> None:
    _, bob = two_users
    victim = uuid.uuid4()
    with (
        as_user(migrated_database["api_url"], bob) as conn,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        conn.execute("insert into app.profiles (user_id) values (%s)", [victim])


def test_no_claims_means_no_rows(two_users, migrated_database) -> None:
    with psycopg.connect(migrated_database["api_url"]) as conn, conn.transaction():
        conn.execute("set local role authenticated")  # but no user claims set
        assert conn.execute("select count(*) from app.profiles").fetchone() == (0,)


def test_api_role_alone_cannot_read_profiles(two_users, migrated_database) -> None:
    """The API must step down to a user to see user data; it has no access of its own."""
    with (
        psycopg.connect(migrated_database["api_url"]) as conn,
        pytest.raises(errors.InsufficientPrivilege),
    ):
        conn.execute("select * from app.profiles")


def test_anonymous_role_has_no_access(two_users, migrated_database) -> None:
    with psycopg.connect(migrated_database["admin_url"]) as conn, conn.transaction():
        conn.execute("set local role anon")
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("select * from app.profiles")


def test_api_role_cannot_delete_or_drop(two_users, migrated_database) -> None:
    with psycopg.connect(migrated_database["api_url"]) as conn:
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("delete from app.answers")
        conn.rollback()
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("drop table app.answers")


def test_deleting_an_account_removes_all_its_data(two_users, migrated_database) -> None:
    alice, _ = two_users
    with psycopg.connect(migrated_database["admin_url"], autocommit=True) as conn:
        conn.execute("delete from auth.users where id = %s", [alice])
        for table in ["profiles", "practice_sessions", "answers", "daily_usage"]:
            row = conn.execute(
                f"select count(*) from app.{table} where user_id = %s",
                [alice],
            ).fetchone()
            assert row == (0,), table
