import logging

from fastapi import APIRouter, HTTPException, Path, Query

from app.exceptions import ReservationConflict
from app.schemas.reservation import ReservationCreate, ReservationRead

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/reservations", tags=["reservations"])

FAKE_DB: dict[int, dict] = {}

NOT_FOUND = {404: {"description": "Réservation inexistante"}}


def _next_id() -> int:
    return max(FAKE_DB, default=0) + 1


def envoyer_notification_annulation(reservation_id: int) -> None:
    """Prévient le propriétaire de l'item (e-mail, à brancher plus tard).

    C'est la seule dépendance externe du router : les tests la remplacent par un `Mock`.
    """
    logger.info("Notification d'annulation pour la réservation %s", reservation_id)


def _get_or_404(reservation_id: int) -> dict:
    reservation = FAKE_DB.get(reservation_id)
    if reservation is None:
        raise HTTPException(
            status_code=404,
            detail=f"Reservation {reservation_id} introuvable",
        )
    return reservation


@router.get(
    "",
    response_model=list[ReservationRead],
    summary="Lister les réservations",
    description="Filtrable par `item_id`. `limit` est plafonné à 100.",
)
def list_reservations(
    item_id: int | None = Query(default=None, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    reservations = list(FAKE_DB.values())
    if item_id is not None:
        reservations = [r for r in reservations if r["item_id"] == item_id]
    return reservations[:limit]


@router.post(
    "",
    response_model=ReservationRead,
    status_code=201,
    summary="Réserver un item",
    description=(
        "Crée une réservation au statut `active`. "
        "`date_fin` doit être strictement postérieure à `date_debut`."
    ),
    responses={422: {"description": "Dates incohérentes ou champ invalide"}},
)
def create_reservation(payload: ReservationCreate):
    reservation_id = _next_id()
    reservation = {"id": reservation_id, **payload.model_dump(), "statut": "active"}
    FAKE_DB[reservation_id] = reservation
    return reservation


@router.get(
    "/{reservation_id}",
    response_model=ReservationRead,
    summary="Consulter une réservation",
    responses=NOT_FOUND,
)
def get_reservation(reservation_id: int = Path(ge=1)):
    return _get_or_404(reservation_id)


@router.post(
    "/{reservation_id}/annuler",
    response_model=ReservationRead,
    summary="Annuler une réservation",
    description=(
        "Passe le statut à `annulee` et notifie le propriétaire. L'opération n'est pas "
        "rejouable. L'annulation est acquise même si la notification échoue."
    ),
    responses={**NOT_FOUND, 409: {"description": "Réservation déjà annulée"}},
)
def cancel_reservation(reservation_id: int = Path(ge=1)):
    reservation = _get_or_404(reservation_id)
    if reservation["statut"] == "annulee":
        raise ReservationConflict(reservation_id, "Reservation déjà annulée")
    reservation["statut"] = "annulee"
    try:
        envoyer_notification_annulation(reservation_id=reservation_id)
    except Exception:
        # Décision : la notification est accessoire, elle ne doit pas faire échouer l'annulation.
        logger.exception("Échec de la notification d'annulation %s", reservation_id)
    return reservation
