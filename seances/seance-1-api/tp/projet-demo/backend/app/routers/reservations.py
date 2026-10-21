from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query

from app.api.deps import get_reservation_service
from app.models.reservation import Reservation
from app.schemas.reservation import ReservationCreate, ReservationRead, ReservationUpdate
from app.services.reservation import ReservationService

router = APIRouter(prefix="/reservations", tags=["reservations"])

NOT_FOUND = {404: {"description": "Réservation inexistante"}}

ReservationServiceDep = Annotated[ReservationService, Depends(get_reservation_service)]


@router.get(
    "",
    response_model=list[ReservationRead],
    summary="Lister les réservations",
    description="Filtrable par `item_id`, paginé par `skip` et `limit` (plafonné à 100).",
)
def list_reservations(
    service: ReservationServiceDep,
    item_id: int | None = Query(default=None, ge=1),
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=20, ge=1, le=100),
) -> list[Reservation]:
    return service.list_reservations(item_id=item_id, skip=skip, limit=limit)


@router.post(
    "",
    response_model=ReservationRead,
    status_code=201,
    summary="Réserver un item",
    description=(
        "Crée une réservation au statut `active`. "
        "`date_fin` doit être strictement postérieure à `date_debut`."
    ),
    responses={
        404: {"description": "Item ou emprunteur inexistant"},
        409: {"description": "Item indisponible ou créneau déjà réservé"},
        422: {"description": "Dates incohérentes ou champ invalide"},
    },
)
def create_reservation(payload: ReservationCreate, service: ReservationServiceDep) -> Reservation:
    return service.creer(
        item_id=payload.item_id,
        borrower_id=payload.borrower_id,
        debut=payload.date_debut,
        fin=payload.date_fin,
    )


@router.get(
    "/{reservation_id}",
    response_model=ReservationRead,
    summary="Consulter une réservation",
    responses=NOT_FOUND,
)
def get_reservation(service: ReservationServiceDep, reservation_id: int = Path(ge=1)) -> Reservation:
    return service.get(reservation_id)


@router.patch(
    "/{reservation_id}",
    response_model=ReservationRead,
    summary="Annuler une réservation",
    description='Seul changement autorisé : `{"statut": "annulee"}`, sur une réservation active.',
    responses={**NOT_FOUND, 409: {"description": "Réservation déjà annulée ou terminée"}},
)
def update_reservation(
    payload: ReservationUpdate, service: ReservationServiceDep, reservation_id: int = Path(ge=1)
) -> Reservation:
    return service.annuler(reservation_id)
