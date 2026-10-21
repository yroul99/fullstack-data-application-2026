from typing import Any

from app.core.exceptions import AccesRefuse, RessourceIntrouvable
from app.models.item import Item
from app.repositories.item import ItemRepository


class ItemService:
    def __init__(self, items: ItemRepository) -> None:
        self.items = items

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

    def create(self, data: dict[str, Any], *, owner_id: int) -> Item:
        return self.items.add(Item(**data, owner_id=owner_id))

    def update(self, item_id: int, data: dict[str, Any], *, current_user_id: int) -> Item:
        item = self._get_owned(item_id, current_user_id)
        for champ, valeur in data.items():
            setattr(item, champ, valeur)
        return self.items.add(item)

    def delete(self, item_id: int, *, current_user_id: int) -> None:
        self.items.delete(self._get_owned(item_id, current_user_id))

    def _get_owned(self, item_id: int, current_user_id: int) -> Item:
        item = self.get(item_id)
        if item.owner_id != current_user_id:
            raise AccesRefuse("Vous n'êtes pas le propriétaire de ce matériel")
        return item
