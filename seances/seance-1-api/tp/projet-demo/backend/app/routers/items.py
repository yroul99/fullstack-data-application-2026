from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Response

from app.api.deps import get_item_service
from app.models.item import Item
from app.schemas.item import ItemCreate, ItemRead, ItemUpdate
from app.services.item import ItemService

router = APIRouter(prefix="/items", tags=["items"])

NOT_FOUND = {404: {"description": "Item inexistant"}}

ItemServiceDep = Annotated[ItemService, Depends(get_item_service)]


@router.get(
    "",
    response_model=list[ItemRead],
    summary="Lister le matériel",
    description=(
        "Renvoie le catalogue, filtré par `q` (titre) et `disponible`, "
        "puis tronqué par `skip` et `limit`."
    ),
)
def list_items(
    service: ItemServiceDep,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    q: str | None = None,
    disponible: bool | None = None,
) -> list[Item]:
    return service.list_items(skip=skip, limit=limit, q=q, disponible=disponible)


# ATTENTION : cette route littérale doit rester AVANT "/{item_id}".
# Déclarée après, "/items/search" serait capturé par "/items/{item_id}",
# qui tenterait de convertir "search" en entier et renverrait 422.
@router.get(
    "/search",
    response_model=list[ItemRead],
    summary="Rechercher du matériel par titre",
    description="Recherche insensible à la casse sur le titre. `q` ne peut pas être vide.",
)
def search_items(service: ItemServiceDep, q: str = Query(min_length=1)) -> list[Item]:
    return service.list_items(q=q)


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    summary="Consulter un item",
    responses=NOT_FOUND,
)
def get_item(service: ItemServiceDep, item_id: int = Path(ge=1)) -> Item:
    return service.get(item_id)


@router.post(
    "",
    response_model=ItemRead,
    status_code=201,
    summary="Publier un item",
    description="Crée un item et lui attribue un identifiant. Les champs inconnus sont refusés.",
)
def create_item(payload: ItemCreate, service: ItemServiceDep) -> Item:
    return service.create(payload.model_dump())


@router.put(
    "/{item_id}",
    response_model=ItemRead,
    summary="Remplacer un item",
    description="Remplace **tous** les champs. Un champ omis reprend sa valeur par défaut.",
    responses=NOT_FOUND,
)
def replace_item(payload: ItemCreate, service: ItemServiceDep, item_id: int = Path(ge=1)) -> Item:
    return service.update(item_id, payload.model_dump())


@router.patch(
    "/{item_id}",
    response_model=ItemRead,
    summary="Modifier partiellement un item",
    description="Ne modifie que les champs réellement transmis ; les autres sont laissés intacts.",
    responses=NOT_FOUND,
)
def update_item(payload: ItemUpdate, service: ItemServiceDep, item_id: int = Path(ge=1)) -> Item:
    return service.update(item_id, payload.model_dump(exclude_unset=True))


@router.delete(
    "/{item_id}",
    status_code=204,
    response_class=Response,
    summary="Supprimer un item",
    description="Supprime l'item. Réponse sans corps.",
    responses={204: {"description": "Item supprimé"}, **NOT_FOUND},
)
def delete_item(service: ItemServiceDep, item_id: int = Path(ge=1)) -> None:
    service.delete(item_id)
