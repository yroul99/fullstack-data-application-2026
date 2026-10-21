from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.models.item import Item


class ItemRepository:
    def __init__(self, db: Session) -> None:
        self.db = db

    def get(self, item_id: int) -> Item | None:
        return self.db.get(Item, item_id)

    def list_items(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        q: str | None = None,
        disponible: bool | None = None,
    ) -> list[Item]:
        stmt = select(Item).options(selectinload(Item.owner))
        if q:
            stmt = stmt.where(Item.titre.ilike(f"%{q}%"))
        if disponible is not None:
            stmt = stmt.where(Item.disponible == disponible)
        stmt = stmt.order_by(Item.created_at.desc()).offset(skip).limit(limit)
        return list(self.db.scalars(stmt))

    def add(self, item: Item) -> Item:
        self.db.add(item)
        self.db.flush()
        self.db.refresh(item)
        return item

    def delete(self, item: Item) -> None:
        self.db.delete(item)
        self.db.flush()
