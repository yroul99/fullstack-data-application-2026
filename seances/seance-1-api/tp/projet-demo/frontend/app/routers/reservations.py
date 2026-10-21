from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from app.api_client import ApiError, api_client
from app.auth import Token
from app.routers.items import reservations_de
from app.templating import templates

router = APIRouter()

MESSAGE_DATES_INVALIDES = "Les dates saisies ne sont pas valides."


@router.post("/items/{item_id}/reservations")
def reserver(
    request: Request,
    item_id: int,
    token: Token,
    date_debut: Annotated[date, Form()],
    date_fin: Annotated[date, Form()],
) -> Response:
    try:
        api_client.create_reservation(token, item_id, date_debut, date_fin)
    except ApiError as exc:
        if exc.status_code not in (409, 422):
            raise  # 401, 404, 503... : le gestionnaire global s'en charge
        # 409 : le backend dit pourquoi (créneau pris, item indisponible, son propre matériel).
        erreur = exc.detail if exc.status_code == 409 else MESSAGE_DATES_INVALIDES
        return templates.TemplateResponse(
            request,
            "items/detail.html",
            {
                "item": api_client.get_item(item_id),
                "reservations": reservations_de(token, item_id),
                "erreur": erreur,
                "saisie": {"date_debut": date_debut, "date_fin": date_fin},
            },
            status_code=exc.status_code,
        )
    return RedirectResponse(f"/items/{item_id}?reservation=ok", status_code=303)


@router.post("/reservations/{reservation_id}")
def changer_statut(
    request: Request,
    reservation_id: int,
    token: Token,
    statut: Annotated[str, Form()],
    item_id: Annotated[int, Form()],
) -> Response:
    try:
        api_client.update_reservation(token, reservation_id, statut)
    except ApiError as exc:
        if exc.status_code != 409:
            raise  # 401, 403, 404... : le gestionnaire global s'en charge
        return templates.TemplateResponse(
            request,
            "items/detail.html",
            {
                "item": api_client.get_item(item_id),
                "reservations": reservations_de(token, item_id),
                "erreur": "Cette réservation est déjà annulée.",
            },
            status_code=409,
        )
    return RedirectResponse(f"/items/{item_id}", status_code=303)
