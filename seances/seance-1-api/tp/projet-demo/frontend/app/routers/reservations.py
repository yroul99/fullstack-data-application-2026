from datetime import date
from typing import Annotated

from fastapi import APIRouter, Form, Request
from fastapi.responses import RedirectResponse, Response

from app.api_client import ApiError, api_client
from app.templating import templates

router = APIRouter()

MESSAGES_RESERVATION = {
    409: "Ce créneau n'est pas disponible.",
    422: "Les dates saisies ne sont pas valides.",
}


@router.post("/items/{item_id}/reservations")
def reserver(
    request: Request,
    item_id: int,
    date_debut: Annotated[date, Form()],
    date_fin: Annotated[date, Form()],
) -> Response:
    try:
        # TODO séance 5 : l'emprunteur sera l'utilisateur connecté (jeton)
        api_client.create_reservation(item_id, 1, date_debut, date_fin)
    except ApiError as exc:
        if exc.status_code not in MESSAGES_RESERVATION:
            raise  # 404, 503... : le gestionnaire global s'en charge
        item = api_client.get_item(item_id)
        reservations = api_client.list_reservations(item_id)
        return templates.TemplateResponse(
            request,
            "items/detail.html",
            {
                "item": item,
                "reservations": reservations,
                "erreur": MESSAGES_RESERVATION[exc.status_code],
                "saisie": {"date_debut": date_debut, "date_fin": date_fin},
            },
            status_code=exc.status_code,
        )
    return RedirectResponse(f"/items/{item_id}?reservation=ok", status_code=303)


@router.post("/reservations/{reservation_id}")
def changer_statut(
    request: Request,
    reservation_id: int,
    statut: Annotated[str, Form()],
    item_id: Annotated[int, Form()],
) -> Response:
    try:
        api_client.update_reservation(reservation_id, statut)
    except ApiError as exc:
        if exc.status_code != 409:
            raise
        item = api_client.get_item(item_id)
        reservations = api_client.list_reservations(item_id)
        return templates.TemplateResponse(
            request,
            "items/detail.html",
            {
                "item": item,
                "reservations": reservations,
                "erreur": "Cette réservation est déjà annulée.",
            },
            status_code=409,
        )
    return RedirectResponse(f"/items/{item_id}", status_code=303)
