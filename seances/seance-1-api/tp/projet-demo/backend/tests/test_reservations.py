from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Item, Reservation, User

RESERVATION_INEXISTANTE = 999_999


def _payload(item_id: int, **champs: Any) -> dict[str, Any]:
    return {"item_id": item_id, "date_debut": "2026-09-01", "date_fin": "2026-09-05", **champs}


@pytest.fixture
def item_tente(db: Session, alice: User) -> Item:
    """Un second item d'Alice."""
    item = Item(owner_id=alice.id, titre="Tente 2 places", tarif_jour=Decimal("12.00"))
    db.add(item)
    db.flush()
    return item


# --- POST /reservations ------------------------------------------------------


def test_creer_reservation_renvoie_201_au_statut_active(
    client_bob: TestClient, item_velo: Item, bob: User
) -> None:
    response = client_bob.post("/reservations", json=_payload(item_velo.id))

    assert response.status_code == 201
    corps = response.json()
    assert isinstance(corps["id"], int)
    assert corps == {
        "id": corps["id"], "item_id": item_velo.id, "borrower_id": bob.id,
        "date_debut": "2026-09-01", "date_fin": "2026-09-05", "statut": "active",
    }


def test_reservation_creee_est_relisible(client_bob: TestClient, item_velo: Item) -> None:
    creee = client_bob.post("/reservations", json=_payload(item_velo.id)).json()

    response = client_bob.get(f"/reservations/{creee['id']}")

    assert response.status_code == 200
    assert response.json() == creee


@pytest.mark.parametrize(
    ("date_debut", "date_fin"),
    [("2026-09-05", "2026-09-01"), ("2026-09-01", "2026-09-01")],
    ids=["inversees", "egales"],
)
def test_creer_reservation_avec_dates_incoherentes_renvoie_422(
    client_bob: TestClient, item_velo: Item, date_debut: str, date_fin: str
) -> None:
    response = client_bob.post("/reservations", json=_payload(
        item_velo.id, date_debut=date_debut, date_fin=date_fin,
    ))

    assert response.status_code == 422
    assert client_bob.get("/reservations").json() == []


@pytest.mark.parametrize(
    ("champs", "champ_en_erreur"),
    [
        ({"item_id": 0}, "item_id"),
        ({"date_debut": "pas-une-date"}, "date_debut"),
        ({"statut": "annulee"}, "statut"),   # le client ne choisit pas le statut
    ],
)
def test_creer_reservation_avec_champ_invalide_renvoie_422(
    client_bob: TestClient, champs: dict[str, Any], champ_en_erreur: str
) -> None:
    response = client_bob.post("/reservations", json={**_payload(1), **champs})

    assert response.status_code == 422
    assert champ_en_erreur in [erreur["loc"][-1] for erreur in response.json()["detail"]]


def test_creer_reservation_sans_date_fin_renvoie_422(client_bob: TestClient) -> None:
    payload = _payload(1)
    del payload["date_fin"]

    response = client_bob.post("/reservations", json=payload)

    assert response.status_code == 422
    assert "date_fin" in [erreur["loc"][-1] for erreur in response.json()["detail"]]


def test_creer_reservation_sur_item_inexistant_renvoie_404(client_bob: TestClient) -> None:
    response = client_bob.post("/reservations", json=_payload(999_999))

    assert response.status_code == 404


def test_creer_reservation_sur_item_indisponible_renvoie_409(
    client_bob: TestClient, db: Session, item_velo: Item
) -> None:
    item_velo.disponible = False
    db.flush()

    response = client_bob.post("/reservations", json=_payload(item_velo.id))

    assert response.status_code == 409


def test_creer_reservation_sur_creneau_deja_pris_renvoie_409(
    client_bob: TestClient, reservation_active: Reservation, item_velo: Item
) -> None:
    response = client_bob.post("/reservations", json=_payload(
        item_velo.id, date_debut="2026-09-03", date_fin="2026-09-08",
    ))

    assert response.status_code == 409
    assert response.json()["detail"] == "Ce créneau est déjà réservé"


# --- GET /reservations -------------------------------------------------------


def test_lister_sans_reservation_renvoie_liste_vide(client_bob: TestClient) -> None:
    response = client_bob.get("/reservations")

    assert response.status_code == 200
    assert response.json() == []


def test_lister_filtre_par_item_id(
    client_bob: TestClient, item_velo: Item, item_tente: Item
) -> None:
    premiere = client_bob.post("/reservations", json=_payload(item_velo.id)).json()
    client_bob.post("/reservations", json=_payload(item_tente.id))
    troisieme = client_bob.post("/reservations", json=_payload(
        item_velo.id, date_debut="2026-10-01", date_fin="2026-10-03",
    )).json()

    response = client_bob.get("/reservations", params={"item_id": item_velo.id})

    assert [r["id"] for r in response.json()] == [premiere["id"], troisieme["id"]]


def test_lister_avec_limit_tronque_la_liste(client_bob: TestClient, item_velo: Item) -> None:
    ids = [
        client_bob.post("/reservations", json=_payload(
            item_velo.id, date_debut=f"2026-0{mois}-01", date_fin=f"2026-0{mois}-05",
        )).json()["id"]
        for mois in (1, 2, 3)
    ]

    response = client_bob.get("/reservations", params={"limit": 2})

    assert [r["id"] for r in response.json()] == ids[:2]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 500}, {"item_id": 0}])
def test_lister_avec_parametre_invalide_renvoie_422(
    client_bob: TestClient, params: dict[str, int]
) -> None:
    response = client_bob.get("/reservations", params=params)

    assert response.status_code == 422


# --- GET /reservations/{reservation_id} --------------------------------------


def test_consulter_reservation_inexistante_renvoie_404(client_bob: TestClient) -> None:
    response = client_bob.get(f"/reservations/{RESERVATION_INEXISTANTE}")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Réservation {RESERVATION_INEXISTANTE} introuvable"


@pytest.mark.parametrize("reservation_id", ["abc", "0"])
def test_consulter_reservation_avec_id_invalide_renvoie_422(
    client_bob: TestClient, reservation_id: str
) -> None:
    response = client_bob.get(f"/reservations/{reservation_id}")

    assert response.status_code == 422


# --- PATCH /reservations/{reservation_id} ------------------------------------

ANNULER = {"statut": "annulee"}


def test_annuler_reservation_passe_le_statut_a_annulee(
    client_bob: TestClient, reservation_active: Reservation
) -> None:
    response = client_bob.patch(f"/reservations/{reservation_active.id}", json=ANNULER)

    assert response.status_code == 200
    assert response.json()["statut"] == "annulee"
    assert client_bob.get(f"/reservations/{reservation_active.id}").json()["statut"] == "annulee"


def test_annuler_une_reservation_deja_annulee_renvoie_409(
    client_bob: TestClient, reservation_active: Reservation
) -> None:
    # Given : la réservation a déjà été annulée.
    client_bob.patch(f"/reservations/{reservation_active.id}", json=ANNULER)

    # When : on demande une seconde annulation.
    response = client_bob.patch(f"/reservations/{reservation_active.id}", json=ANNULER)

    # Then : l'API refuse avec un conflit, et la réservation reste annulée.
    assert response.status_code == 409
    assert client_bob.get(f"/reservations/{reservation_active.id}").json()["statut"] == "annulee"


def test_annuler_reservation_inexistante_renvoie_404(client_bob: TestClient) -> None:
    response = client_bob.patch(f"/reservations/{RESERVATION_INEXISTANTE}", json=ANNULER)

    assert response.status_code == 404


@pytest.mark.parametrize("payload", [{"statut": "active"}, {"statut": "terminee"}, {}])
def test_patch_reservation_n_accepte_que_l_annulation(
    client_bob: TestClient, reservation_active: Reservation, payload: dict[str, str]
) -> None:
    response = client_bob.patch(f"/reservations/{reservation_active.id}", json=payload)

    assert response.status_code == 422
