from collections.abc import Generator
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.core.security import decode_access_token
from app.db.session import SessionLocal
from app.models.user import User
from app.repositories.item import ItemRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.user import UserRepository
from app.services.auth import AuthService
from app.services.item import ItemService
from app.services.reservation import ReservationService


def get_db() -> Generator[Session, None, None]:
    """Une session par requête HTTP : chaque requête est une transaction."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


DbSession = Annotated[Session, Depends(get_db)]

# auto_error=False : sans jeton, on lève notre propre 401, identique aux autres causes.
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/login", auto_error=False)

CREDENTIALS_EXCEPTION: HTTPException = HTTPException(
    status_code=401,
    detail="Identifiants invalides",
    headers={"WWW-Authenticate": "Bearer"},
)


def get_current_user(
    token: Annotated[str | None, Depends(oauth2_scheme)],
    db: DbSession,
) -> User:
    if token is None:
        raise CREDENTIALS_EXCEPTION
    try:
        user_id = decode_access_token(token)
    except (jwt.PyJWTError, KeyError, ValueError):
        raise CREDENTIALS_EXCEPTION

    user = UserRepository(db).get(user_id)
    if user is None:
        raise CREDENTIALS_EXCEPTION
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def get_item_service(db: DbSession) -> ItemService:
    return ItemService(ItemRepository(db))


def get_reservation_service(db: DbSession) -> ReservationService:
    return ReservationService(ReservationRepository(db), ItemRepository(db))


def get_auth_service(db: DbSession) -> AuthService:
    return AuthService(UserRepository(db))
