from fastapi import APIRouter, HTTPException, Path, Query, Response

from app.schemas.item import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])

FAKE_DB: dict[int, dict] = {}
_next_id = 1

NOT_FOUND = {404: {"description": "Item inexistant"}}


def _get_or_404(item_id: int) -> dict:
    item = FAKE_DB.get(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail=f"Item {item_id} introuvable")
    return item


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
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
    q: str | None = None,
    disponible: bool | None = None,
):
    items = list(FAKE_DB.values())
    if q is not None:
        items = [i for i in items if q.lower() in i["titre"].lower()]
    if disponible is not None:
        items = [i for i in items if i["disponible"] == disponible]
    return items[skip : skip + limit]


# ATTENTION : cette route littérale doit rester AVANT "/{item_id}".
# Déclarée après, "/items/search" serait capturé par "/items/{item_id}",
# qui tenterait de convertir "search" en entier et renverrait 422.
@router.get(
    "/search",
    response_model=list[ItemRead],
    summary="Rechercher du matériel par titre",
    description="Recherche insensible à la casse sur le titre. `q` ne peut pas être vide.",
)
def search_items(q: str = Query(min_length=1)):
    return [i for i in FAKE_DB.values() if q.lower() in i["titre"].lower()]


@router.get(
    "/{item_id}",
    response_model=ItemRead,
    summary="Consulter un item",
    responses=NOT_FOUND,
)
def get_item(item_id: int = Path(ge=1)):
    return _get_or_404(item_id)


@router.post(
    "",
    response_model=ItemRead,
    status_code=201,
    summary="Publier un item",
    description="Crée un item et lui attribue un identifiant. Les champs inconnus sont refusés.",
)
def create_item(payload: ItemCreate):
    global _next_id
    item = {"id": _next_id, **payload.model_dump()}
    FAKE_DB[_next_id] = item
    _next_id += 1
    return item


@router.put(
    "/{item_id}",
    response_model=ItemRead,
    summary="Remplacer un item",
    description="Remplace **tous** les champs. Un champ omis reprend sa valeur par défaut.",
    responses=NOT_FOUND,
)
def replace_item(payload: ItemCreate, item_id: int = Path(ge=1)):
    _get_or_404(item_id)
    item = {"id": item_id, **payload.model_dump()}
    FAKE_DB[item_id] = item
    return item


@router.patch(
    "/{item_id}",
    response_model=ItemRead,
    summary="Modifier partiellement un item",
    description="Ne modifie que les champs réellement transmis ; les autres sont laissés intacts.",
    responses=NOT_FOUND,
)
def update_item(payload: ItemUpdate, item_id: int = Path(ge=1)):
    item = _get_or_404(item_id)
    item.update(payload.model_dump(exclude_unset=True))
    return item


@router.delete(
    "/{item_id}",
    status_code=204,
    response_class=Response,
    summary="Supprimer un item",
    description="Supprime l'item. Réponse sans corps.",
    responses={204: {"description": "Item supprimé"}, **NOT_FOUND},
)
def delete_item(item_id: int = Path(ge=1)):
    _get_or_404(item_id)
    del FAKE_DB[item_id]
