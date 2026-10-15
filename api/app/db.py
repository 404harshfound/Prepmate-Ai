"""Database access.

The API logs in to Postgres as `prepmate_api`, a role that owns nothing and
can do very little on its own. For every signed-in request it steps down to
the `authenticated` role inside a transaction and tells Postgres who the user
is. Row-level security then filters every query, so a missing WHERE clause in
our code still cannot return another user's rows.

`SET LOCAL` and `set_config(..., true)` last only until the transaction ends,
which makes this safe with pooled connections (including Supabase's
transaction-mode pooler).
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

from psycopg import AsyncConnection
from psycopg.rows import DictRow, dict_row
from psycopg_pool import AsyncConnectionPool

from app.auth import AuthUser

STATEMENT_TIMEOUT = "10s"
READINESS_TIMEOUT_SECONDS = 3.0

Connection = AsyncConnection[DictRow]


class Database:
    def __init__(self, conninfo: str, *, max_size: int = 5) -> None:
        self._pool: AsyncConnectionPool[Connection] = AsyncConnectionPool(
            conninfo,
            connection_class=AsyncConnection[DictRow],
            min_size=1,
            max_size=max_size,
            open=False,
            timeout=5.0,  # how long a request waits for a free connection
            max_lifetime=1800.0,
            check=AsyncConnectionPool.check_connection,  # drop dead connections
            kwargs={
                "row_factory": dict_row,
                # Transaction-mode poolers cannot keep prepared statements.
                "prepare_threshold": None,
                "connect_timeout": 5,
                "application_name": "prepmate-api",
            },
        )

    async def open(self) -> None:
        # Do not block start-up on the database: the app should boot, report
        # "not ready", and recover by itself when the database comes back.
        await self._pool.open(wait=False)

    async def close(self) -> None:
        await self._pool.close()

    @asynccontextmanager
    async def as_user(self, user: AuthUser) -> AsyncIterator[Connection]:
        """A transaction that can only see and change this user's rows."""
        async with self._pool.connection() as conn, conn.transaction():
            await conn.execute(
                "select set_config('statement_timeout', %s, true),"
                " set_config('request.jwt.claims', %s, true)",
                [STATEMENT_TIMEOUT, user.db_claims],
            )
            await conn.execute("set local role authenticated")
            yield conn

    @asynccontextmanager
    async def as_service(self) -> AsyncIterator[Connection]:
        """A transaction as the API itself, for work no user may do directly."""
        async with self._pool.connection() as conn, conn.transaction():
            await conn.execute(
                "select set_config('statement_timeout', %s, true)", [STATEMENT_TIMEOUT]
            )
            yield conn

    async def is_ready(self) -> bool:
        try:
            async with asyncio.timeout(READINESS_TIMEOUT_SECONDS):
                async with self._pool.connection() as conn:
                    await conn.execute("select 1")
            return True
        except Exception:
            return False


async def fetch_one(conn: Connection, query: Any, params: Any = None) -> DictRow | None:
    cursor = await conn.execute(query, params)
    return await cursor.fetchone()
