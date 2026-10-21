from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response

from app.api_client import ApiError, api_client
from app.auth import Token
from app.templating import templates

router = APIRouter()


def reservations_de(token: str | None, item_id: int) -> list[dict]:
    """Les réservations d'un item. Un visiteur sans jeton ne les voit pas (route authentifiée)."""
    return api_client.list_reservations(token, item_id) if token else []


@router.get("/items", response_class=HTMLResponse)
def list_items_page(request: Request) -> HTMLResponse:
    items = api_client.list_items()
    return templates.TemplateResponse(request, "items/list.html", {"items": items})


@router.get("/items/new", response_class=HTMLResponse)
def new_item_page(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(request, "items/form.html", {})


@router.post("/items")
def create_item(
    request: Request,
    token: Token,
    titre: Annotated[str, Form()],
    tarif_jour: Annotated[float, Form()],
    description: Annotated[str, Form()] = "",
    disponible: Annotated[bool, Form()] = False,
) -> Response:
    data = {
        "titre": titre,
        "description": description or None,
        "tarif_jour": tarif_jour,
        "disponible": disponible,
    }
    try:
        item = api_client.create_item(token, data)
    except ApiError as exc:
        if exc.status_code != 422:
            raise  # 401, 503... : le gestionnaire global s'en charge
        return templates.TemplateResponse(
            request,
            "items/form.html",
            {"erreurs": exc.messages(), "saisie": data},
            status_code=422,
        )
    return RedirectResponse(f"/items/{item['id']}", status_code=303)


@router.get("/items/{item_id}", response_class=HTMLResponse)
def item_detail_page(request: Request, item_id: int, token: Token) -> HTMLResponse:
    item = api_client.get_item(item_id)
    reservations = reservations_de(token, item_id)
    return templates.TemplateResponse(
        request, "items/detail.html", {"item": item, "reservations": reservations}
    )
