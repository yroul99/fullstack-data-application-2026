from decimal import Decimal
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.models import Item, User

ITEM_INEXISTANT = 999_999


def _creer_item(client: TestClient, **champs: Any) -> dict[str, Any]:
    payload = {"titre": "Item de test", "tarif_jour": 5.0, **champs}
    response = client.post("/items", json=payload)
    assert response.status_code == 201
    return response.json()


def _inserer_items(db: Session, owner: User, nombre: int) -> list[int]:
    """Insère des items sans passer par autant de requêtes HTTP ; renvoie leurs id."""
    items = [Item(owner_id=owner.id, titre=f"Item {i}", tarif_jour=Decimal("5.00"))
             for i in range(1, nombre + 1)]
    db.add_all(items)
    db.flush()
    return [item.id for item in items]


# --- POST /items -------------------------------------------------------------


def test_creer_item_renvoie_201_et_l_item_avec_un_id(client_alice: TestClient, alice: User) -> None:
    response = client_alice.post("/items", json={"titre": "Vélo de ville", "tarif_jour": 8.5})

    assert response.status_code == 201
    corps = response.json()
    assert isinstance(corps["id"], int)
    assert corps["titre"] == "Vélo de ville"
    assert corps["tarif_jour"] == "8.50"
    assert corps["disponible"] is True
    assert corps["description"] is None
    assert corps["owner"] == {"id": alice.id, "display_name": "Alice"}


def test_item_cree_est_relisible(client: TestClient, client_alice: TestClient) -> None:
    cree = _creer_item(client_alice, titre="Vélo de ville")

    response = client.get(f"/items/{cree['id']}")

    assert response.status_code == 200
    assert response.json() == cree


def test_ids_successifs_sont_distincts(client_alice: TestClient) -> None:
    premier = _creer_item(client_alice, titre="Tente")
    second = _creer_item(client_alice, titre="Réchaud")

    assert second["id"] > premier["id"]


@pytest.mark.parametrize(
    ("payload", "champ_en_erreur"),
    [
        ({"titre": "ab", "tarif_jour": 8.5}, "titre"),                   # trop court
        ({"titre": "x" * 121, "tarif_jour": 8.5}, "titre"),              # trop long
        ({"titre": "Vélo de ville", "tarif_jour": 0}, "tarif_jour"),      # nul
        ({"titre": "Vélo de ville", "tarif_jour": -3}, "tarif_jour"),     # négatif
        ({"titre": "Vélo de ville"}, "tarif_jour"),                       # manquant
        ({"tarif_jour": 8.5}, "titre"),                                   # manquant
        ({"titre": "Vélo de ville", "tarif_jour": 8.5, "couleur": "rouge"}, "couleur"),  # inconnu
    ],
)
def test_creation_item_invalide_renvoie_422(
    client_alice: TestClient, payload: dict[str, Any], champ_en_erreur: str
) -> None:
    response = client_alice.post("/items", json=payload)

    assert response.status_code == 422
    champs = [erreur["loc"][-1] for erreur in response.json()["detail"]]
    assert champ_en_erreur in champs


def test_creation_item_invalide_ne_cree_rien(client: TestClient, client_alice: TestClient) -> None:
    client_alice.post("/items", json={"titre": "ab", "tarif_jour": 8.5})

    assert client.get("/items").json() == []


# --- GET /items --------------------------------------------------------------


def test_lister_sans_item_renvoie_liste_vide(client: TestClient) -> None:
    response = client.get("/items")

    assert response.status_code == 200
    assert response.json() == []


def test_lister_filtre_par_q_sans_tenir_compte_de_la_casse(
    client: TestClient, client_alice: TestClient
) -> None:
    _creer_item(client_alice, titre="Vélo de ville")
    _creer_item(client_alice, titre="Tente 2 places")

    response = client.get("/items", params={"q": "VÉLO"})

    assert [item["titre"] for item in response.json()] == ["Vélo de ville"]


def test_lister_filtre_par_disponible(client: TestClient, client_alice: TestClient) -> None:
    _creer_item(client_alice, titre="Vélo de ville", disponible=True)
    _creer_item(client_alice, titre="Tente 2 places", disponible=False)

    response = client.get("/items", params={"disponible": False})

    assert [item["titre"] for item in response.json()] == ["Tente 2 places"]


def test_lister_avec_skip_saute_les_premiers(client: TestClient, db: Session, alice: User) -> None:
    # Given : cinquante items, insérés sans passer par cinquante requêtes HTTP.
    ids = _inserer_items(db, alice, 50)

    response = client.get("/items", params={"skip": 40, "limit": 20})

    # La liste est triée du plus récent au plus ancien : les 10 derniers sont les 10 premiers créés.
    assert [item["id"] for item in response.json()] == sorted(ids[:10], reverse=True)


def test_lister_sans_limit_renvoie_20_items_au_plus(client: TestClient, db: Session, alice: User) -> None:
    _inserer_items(db, alice, 30)

    response = client.get("/items")

    assert len(response.json()) == 20


@pytest.mark.parametrize(
    "params",
    [{"limit": 0}, {"limit": 101}, {"limit": 500}, {"skip": -1}, {"disponible": "peut-etre"}],
)
def test_lister_avec_parametre_invalide_renvoie_422(
    client: TestClient, params: dict[str, Any]
) -> None:
    response = client.get("/items", params=params)

    assert response.status_code == 422


# --- GET /items/search -------------------------------------------------------


def test_search_trouve_les_items_par_titre(
    client: TestClient, client_alice: TestClient, item_velo: Item
) -> None:
    _creer_item(client_alice, titre="Tente 2 places")

    response = client.get("/items/search", params={"q": "vélo"})

    assert response.status_code == 200
    assert [item["id"] for item in response.json()] == [item_velo.id]


@pytest.mark.parametrize("params", [{}, {"q": ""}])
def test_search_sans_q_renvoie_422(client: TestClient, params: dict[str, str]) -> None:
    response = client.get("/items/search", params=params)

    assert response.status_code == 422
    assert [erreur["loc"][-1] for erreur in response.json()["detail"]] == ["q"]


# --- GET /items/{item_id} ----------------------------------------------------


def test_consulter_item_inexistant_renvoie_404(client: TestClient) -> None:
    response = client.get(f"/items/{ITEM_INEXISTANT}")

    assert response.status_code == 404


@pytest.mark.parametrize("item_id", ["abc", "0", "-1"])
def test_consulter_item_avec_id_invalide_renvoie_422(client: TestClient, item_id: str) -> None:
    response = client.get(f"/items/{item_id}")

    assert response.status_code == 422


# --- PUT /items/{item_id} ----------------------------------------------------


def test_remplacer_item_remplace_tous_les_champs(
    client: TestClient, client_alice: TestClient, item_velo: Item, alice: User
) -> None:
    response = client_alice.put(f"/items/{item_velo.id}", json={
        "titre": "Vélo pliant", "tarif_jour": 10, "disponible": False,
    })

    assert response.status_code == 200
    assert response.json() == {
        "id": item_velo.id, "titre": "Vélo pliant", "description": None,
        "tarif_jour": "10.00", "disponible": False,
        "owner": {"id": alice.id, "display_name": "Alice"},
    }
    assert client.get(f"/items/{item_velo.id}").json() == response.json()


def test_remplacer_item_avec_corps_invalide_renvoie_422_et_ne_modifie_rien(
    client: TestClient, client_alice: TestClient, item_velo: Item
) -> None:
    avant = client.get(f"/items/{item_velo.id}").json()

    response = client_alice.put(f"/items/{item_velo.id}", json={"titre": "ab", "tarif_jour": 10})

    assert response.status_code == 422
    assert client.get(f"/items/{item_velo.id}").json() == avant


# --- PATCH /items/{item_id} --------------------------------------------------


def test_modifier_un_seul_champ_laisse_les_autres_intacts(
    client: TestClient, client_alice: TestClient, item_velo: Item
) -> None:
    avant = client.get(f"/items/{item_velo.id}").json()

    response = client_alice.patch(f"/items/{item_velo.id}", json={"titre": "Vélo pliant"})

    assert response.status_code == 200
    assert response.json() == {**avant, "titre": "Vélo pliant"}
    assert client.get(f"/items/{item_velo.id}").json()["description"] == "Trois vitesses"


def test_modifier_sans_champ_ne_change_rien(
    client: TestClient, client_alice: TestClient, item_velo: Item
) -> None:
    avant = client.get(f"/items/{item_velo.id}").json()

    response = client_alice.patch(f"/items/{item_velo.id}", json={})

    assert response.status_code == 200
    assert response.json() == avant


@pytest.mark.parametrize(
    ("payload", "champ_en_erreur"),
    [
        ({"titre": "ab"}, "titre"),
        ({"tarif_jour": 0}, "tarif_jour"),
        ({"couleur": "rouge"}, "couleur"),
    ],
)
def test_modifier_avec_champ_invalide_renvoie_422(
    client_alice: TestClient, item_velo: Item, payload: dict[str, Any], champ_en_erreur: str
) -> None:
    response = client_alice.patch(f"/items/{item_velo.id}", json=payload)

    assert response.status_code == 422
    assert champ_en_erreur in [erreur["loc"][-1] for erreur in response.json()["detail"]]


# --- DELETE /items/{item_id} -------------------------------------------------


def test_supprimer_item_renvoie_204_sans_corps(client_alice: TestClient, item_velo: Item) -> None:
    response = client_alice.delete(f"/items/{item_velo.id}")

    assert response.status_code == 204
    assert response.content == b""


def test_item_supprime_n_est_plus_consultable(
    client: TestClient, client_alice: TestClient, item_velo: Item
) -> None:
    client_alice.delete(f"/items/{item_velo.id}")

    assert client.get(f"/items/{item_velo.id}").status_code == 404
    assert client.get("/items").json() == []


# --- 404 sur toutes les routes d'un item -------------------------------------


@pytest.mark.parametrize(
    ("methode", "payload"),
    [
        ("GET", None),
        ("PUT", {"titre": "Vélo pliant", "tarif_jour": 10}),
        ("PATCH", {"titre": "Vélo pliant"}),
        ("DELETE", None),
    ],
)
def test_route_sur_item_inexistant_renvoie_404(
    client_alice: TestClient, methode: str, payload: dict[str, Any] | None
) -> None:
    response = client_alice.request(methode, f"/items/{ITEM_INEXISTANT}", json=payload)

    assert response.status_code == 404
    assert response.json()["detail"] == f"Item {ITEM_INEXISTANT} introuvable"
