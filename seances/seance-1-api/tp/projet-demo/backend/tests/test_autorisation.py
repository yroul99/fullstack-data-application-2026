"""La matrice d'autorisation : chaque ligne, trois tests — anonyme, propriétaire, autre utilisateur.

| Action                                   | Qui a le droit                                 |
|------------------------------------------|------------------------------------------------|
| GET /items, GET /items/{id}              | Tout le monde                                  |
| POST /items                              | Authentifié ; propriétaire = l'auteur du jeton |
| PUT, PATCH, DELETE /items/{id}           | Le propriétaire de l'item                      |
| POST /reservations                       | Authentifié, sauf le propriétaire de l'item    |
| GET /reservations, GET /reservations/{id}| Authentifié                                    |
| PATCH /reservations/{id} (annulation)    | L'emprunteur ou le propriétaire de l'item      |
| GET /auth/me                             | Authentifié                                    |
"""

from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.core.exceptions import AccesRefuse
from app.models import Item, Reservation, User
from app.repositories.item import ItemRepository
from app.services.item import ItemService

ITEM = {"titre": "Vélo", "tarif_jour": 8.5}
RESERVATION = {"date_debut": "2026-10-01", "date_fin": "2026-10-03"}


@pytest.fixture
def clients(
    client: TestClient, client_alice: TestClient, client_bob: TestClient, client_carol: TestClient
) -> dict[str, TestClient]:
    return {"anonyme": client, "alice": client_alice, "bob": client_bob, "carol": client_carol}


def _assert_401(response: Any) -> None:
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


# --- GET /items, GET /items/{id} : publics -----------------------------------


@pytest.mark.parametrize("qui", ["anonyme", "alice", "bob"])
def test_lecture_du_catalogue_est_publique(
    clients: dict[str, TestClient], item_velo: Item, qui: str
) -> None:
    assert clients[qui].get("/items").status_code == 200
    assert clients[qui].get(f"/items/{item_velo.id}").status_code == 200


# --- POST /items ---------------------------------------------------------------


def test_anonyme_ne_peut_pas_creer_item(client: TestClient) -> None:
    _assert_401(client.post("/items", json=ITEM))


@pytest.mark.parametrize("qui", ["alice", "bob"])
def test_item_cree_appartient_a_l_auteur_du_jeton(
    clients: dict[str, TestClient], alice: User, bob: User, qui: str
) -> None:
    response = clients[qui].post("/items", json=ITEM)

    assert response.status_code == 201
    assert response.json()["owner"]["id"] == {"alice": alice, "bob": bob}[qui].id


def test_owner_id_dans_le_corps_ne_permet_pas_d_usurper_bob(
    client_alice: TestClient, db: Session, bob: User
) -> None:
    # Le schéma de création refuse les champs inconnus (séance 1) : owner_id est rejeté.
    response = client_alice.post("/items", json={**ITEM, "owner_id": bob.id})

    assert response.status_code == 422
    assert "owner_id" in [erreur["loc"][-1] for erreur in response.json()["detail"]]
    assert db.query(Item).filter_by(owner_id=bob.id).count() == 0


# --- PUT, PATCH, DELETE /items/{id} : propriétaire uniquement ----------------

ECRITURES_ITEM = [
    ("PUT", {"titre": "Vélo pliant", "tarif_jour": 10}, 200),
    ("PATCH", {"tarif_jour": 9}, 200),
    ("DELETE", None, 204),
]


@pytest.mark.parametrize(("methode", "payload", "_succes"), ECRITURES_ITEM)
def test_anonyme_ne_peut_pas_modifier_item(
    client: TestClient, item_velo: Item, methode: str, payload: Any, _succes: int
) -> None:
    _assert_401(client.request(methode, f"/items/{item_velo.id}", json=payload))


@pytest.mark.parametrize(("methode", "payload", "succes"), ECRITURES_ITEM)
def test_proprietaire_peut_modifier_item(
    client_alice: TestClient, item_velo: Item, methode: str, payload: Any, succes: int
) -> None:
    assert client_alice.request(methode, f"/items/{item_velo.id}", json=payload).status_code == succes


@pytest.mark.parametrize(("methode", "payload", "_succes"), ECRITURES_ITEM)
def test_autre_utilisateur_ne_peut_pas_modifier_item(
    client: TestClient, client_bob: TestClient, item_velo: Item,
    methode: str, payload: Any, _succes: int,
) -> None:
    avant = client.get(f"/items/{item_velo.id}").json()

    response = client_bob.request(methode, f"/items/{item_velo.id}", json=payload)

    assert response.status_code == 403
    assert client.get(f"/items/{item_velo.id}").json() == avant


# --- POST /reservations --------------------------------------------------------


def test_anonyme_ne_peut_pas_reserver(client: TestClient, item_velo: Item) -> None:
    _assert_401(client.post("/reservations", json={"item_id": item_velo.id, **RESERVATION}))


def test_proprietaire_ne_peut_pas_reserver_son_propre_item(
    client_alice: TestClient, item_velo: Item
) -> None:
    response = client_alice.post("/reservations", json={"item_id": item_velo.id, **RESERVATION})

    assert response.status_code == 409


def test_autre_utilisateur_reserve_en_son_nom(
    client_bob: TestClient, item_velo: Item, bob: User
) -> None:
    response = client_bob.post("/reservations", json={"item_id": item_velo.id, **RESERVATION})

    assert response.status_code == 201
    assert response.json()["borrower_id"] == bob.id


# --- GET /reservations, GET /reservations/{id} : authentifié ------------------


def test_anonyme_ne_peut_pas_lire_les_reservations(
    client: TestClient, reservation_active: Reservation
) -> None:
    _assert_401(client.get("/reservations"))
    _assert_401(client.get(f"/reservations/{reservation_active.id}"))


@pytest.mark.parametrize("qui", ["alice", "bob"])
def test_utilisateur_connecte_peut_lire_les_reservations(
    clients: dict[str, TestClient], reservation_active: Reservation, qui: str
) -> None:
    assert clients[qui].get("/reservations").status_code == 200
    assert clients[qui].get(f"/reservations/{reservation_active.id}").status_code == 200


# --- PATCH /reservations/{id} : emprunteur ou propriétaire de l'item ---------

ANNULER = {"statut": "annulee"}


def test_anonyme_ne_peut_pas_annuler(client: TestClient, reservation_active: Reservation) -> None:
    _assert_401(client.patch(f"/reservations/{reservation_active.id}", json=ANNULER))


@pytest.mark.parametrize("qui", ["bob", "alice"], ids=["emprunteur", "proprietaire-item"])
def test_emprunteur_ou_proprietaire_peut_annuler(
    clients: dict[str, TestClient], reservation_active: Reservation, qui: str
) -> None:
    response = clients[qui].patch(f"/reservations/{reservation_active.id}", json=ANNULER)

    assert response.status_code == 200
    assert response.json()["statut"] == "annulee"


def test_autre_utilisateur_ne_peut_pas_annuler(
    client_carol: TestClient, client_bob: TestClient, reservation_active: Reservation
) -> None:
    response = client_carol.patch(f"/reservations/{reservation_active.id}", json=ANNULER)

    assert response.status_code == 403
    assert client_bob.get(f"/reservations/{reservation_active.id}").json()["statut"] == "active"


# --- GET /auth/me ------------------------------------------------------------


def test_anonyme_n_a_pas_de_me(client: TestClient) -> None:
    _assert_401(client.get("/auth/me"))


@pytest.mark.parametrize("qui", ["alice", "bob"])
def test_me_renvoie_l_auteur_du_jeton(
    clients: dict[str, TestClient], alice: User, bob: User, qui: str
) -> None:
    response = clients[qui].get("/auth/me")

    assert response.status_code == 200
    assert response.json()["id"] == {"alice": alice, "bob": bob}[qui].id


# --- La règle de propriété, testée dans le service, sans HTTP ---------------


@pytest.fixture
def item_service(db: Session) -> ItemService:
    return ItemService(ItemRepository(db))


def test_supprimer_l_item_d_un_autre_leve_acces_refuse(
    item_service: ItemService, item_velo: Item, bob: User
) -> None:
    with pytest.raises(AccesRefuse):
        item_service.delete(item_velo.id, current_user_id=bob.id)


def test_le_proprietaire_peut_supprimer_son_item_via_le_service(
    item_service: ItemService, item_velo: Item, alice: User
) -> None:
    item_service.delete(item_velo.id, current_user_id=alice.id)

    assert ItemRepository(item_service.items.db).get(item_velo.id) is None
