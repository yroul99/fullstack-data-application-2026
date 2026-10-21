from collections.abc import Generator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.db.session import SessionLocal
from app.repositories.item import ItemRepository
from app.repositories.reservation import ReservationRepository
from app.repositories.user import UserRepository
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


def get_item_service(db: DbSession) -> ItemService:
    return ItemService(ItemRepository(db), UserRepository(db))


def get_reservation_service(db: DbSession) -> ReservationService:
    return ReservationService(ReservationRepository(db), ItemRepository(db), UserRepository(db))
