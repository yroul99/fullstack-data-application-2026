from typing import Any

from app.core.exceptions import RessourceIntrouvable
from app.models.item import Item
from app.repositories.item import ItemRepository
from app.repositories.user import UserRepository


class ItemService:
    def __init__(self, items: ItemRepository, users: UserRepository) -> None:
        self.items = items
        self.users = users

    def get(self, item_id: int) -> Item:
        item = self.items.get(item_id)
        if item is None:
            raise RessourceIntrouvable(f"Item {item_id} introuvable")
        return item

    def list_items(
        self,
        *,
        skip: int = 0,
        limit: int = 20,
        q: str | None = None,
        disponible: bool | None = None,
    ) -> list[Item]:
        return self.items.list_items(skip=skip, limit=limit, q=q, disponible=disponible)

    def create(self, data: dict[str, Any]) -> Item:
        self._check_owner(data["owner_id"])
        return self.items.add(Item(**data))

    def update(self, item_id: int, data: dict[str, Any]) -> Item:
        item = self.get(item_id)
        if "owner_id" in data:
            self._check_owner(data["owner_id"])
        for champ, valeur in data.items():
            setattr(item, champ, valeur)
        return self.items.add(item)

    def delete(self, item_id: int) -> None:
        self.items.delete(self.get(item_id))

    def _check_owner(self, owner_id: int) -> None:
        if self.users.get(owner_id) is None:
            raise RessourceIntrouvable(f"Utilisateur {owner_id} introuvable")
