"""Tests unitaires des schémas Pydantic : ni `client`, ni `storage`, donc aucune préparation."""

from datetime import date

import pytest
from pydantic import ValidationError

from app.schemas.item import ItemCreate, ItemUpdate
from app.schemas.reservation import ReservationCreate


def test_reservation_valide_est_acceptee() -> None:
    reservation = ReservationCreate(item_id=1, date_debut=date(2026, 9, 1), date_fin=date(2026, 9, 5))

    assert reservation.date_fin > reservation.date_debut


def test_dates_inversees_sont_refusees_par_le_schema() -> None:
    with pytest.raises(ValidationError, match="date_fin"):
        ReservationCreate(item_id=1, date_debut=date(2026, 9, 5), date_fin=date(2026, 9, 1))


def test_dates_egales_sont_refusees_par_le_schema() -> None:
    with pytest.raises(ValidationError, match="date_fin"):
        ReservationCreate(item_id=1, date_debut=date(2026, 9, 1), date_fin=date(2026, 9, 1))


def test_reservation_refuse_un_champ_inconnu() -> None:
    with pytest.raises(ValidationError, match="statut"):
        ReservationCreate(
            item_id=1, date_debut=date(2026, 9, 1), date_fin=date(2026, 9, 5), statut="annulee",
        )


def test_item_est_disponible_par_defaut() -> None:
    assert ItemCreate(titre="Vélo de ville", tarif_jour=8.5).disponible is True


def test_item_update_sans_champ_est_vide() -> None:
    assert ItemUpdate().model_dump(exclude_unset=True) == {}


def test_item_update_ne_garde_que_les_champs_transmis() -> None:
    assert ItemUpdate(titre="Vélo pliant").model_dump(exclude_unset=True) == {"titre": "Vélo pliant"}
