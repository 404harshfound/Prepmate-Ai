"""Request dependencies shared by the routers."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import AuthUnavailableError, AuthUser, InvalidTokenError, TokenVerifier
from app.config import Settings
from app.db import Database

_bearer = HTTPBearer(auto_error=False, description="Supabase access token")


def get_database(request: Request) -> Database:
    database: Database = request.app.state.database
    return database


def get_verifier(request: Request) -> TokenVerifier:
    verifier: TokenVerifier = request.app.state.verifier
    return verifier


# Deliberately a plain `def`: FastAPI runs it in a worker thread, so the rare
# blocking fetch of the signing keys never stalls the event loop.
def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    verifier: Annotated[TokenVerifier, Depends(get_verifier)],
) -> AuthUser:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Sign in to continue.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    try:
        return verifier.verify(credentials.credentials)
    except InvalidTokenError as exc:
        # One message for every failure reason: no hints for an attacker.
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Your session is invalid or has expired. Sign in again.",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc
    except AuthUnavailableError as exc:
        raise HTTPException(
            status.HTTP_503_SERVICE_UNAVAILABLE,
            "Sign-in checks are temporarily unavailable. Try again in a minute.",
            headers={"Retry-After": "30"},
        ) from exc


def get_settings(request: Request) -> Settings:
    settings: Settings = request.app.state.settings
    return settings


CurrentUser = Annotated[AuthUser, Depends(get_current_user)]
Db = Annotated[Database, Depends(get_database)]
AppSettings = Annotated[Settings, Depends(get_settings)]
