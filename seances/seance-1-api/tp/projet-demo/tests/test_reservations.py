from typing import Any
from unittest.mock import Mock

import pytest
from fastapi.testclient import TestClient

from app.routers import reservations

RESERVATION_INEXISTANTE = 999


def _payload(item_id: int, **champs: Any) -> dict[str, Any]:
    return {"item_id": item_id, "date_debut": "2026-09-01", "date_fin": "2026-09-05", **champs}


@pytest.fixture
def notifier(monkeypatch: pytest.MonkeyPatch) -> Mock:
    """Remplace la notification d'annulation, seule dépendance externe du router."""
    mock = Mock()
    monkeypatch.setattr(reservations, "envoyer_notification_annulation", mock)
    return mock


# --- POST /reservations ------------------------------------------------------


def test_creer_reservation_renvoie_201_au_statut_active(
    client: TestClient, item_velo: dict[str, Any]
) -> None:
    response = client.post("/reservations", json=_payload(item_velo["id"]))

    assert response.status_code == 201
    assert response.json() == {
        "id": 1, "item_id": item_velo["id"],
        "date_debut": "2026-09-01", "date_fin": "2026-09-05", "statut": "active",
    }


def test_reservation_creee_est_relisible(
    client: TestClient, reservation_active: dict[str, Any]
) -> None:
    response = client.get(f"/reservations/{reservation_active['id']}")

    assert response.status_code == 200
    assert response.json() == reservation_active


@pytest.mark.parametrize(
    ("date_debut", "date_fin"),
    [("2026-09-05", "2026-09-01"), ("2026-09-01", "2026-09-01")],
    ids=["inversees", "egales"],
)
def test_creer_reservation_avec_dates_incoherentes_renvoie_422(
    client: TestClient, item_velo: dict[str, Any], date_debut: str, date_fin: str
) -> None:
    response = client.post("/reservations", json=_payload(
        item_velo["id"], date_debut=date_debut, date_fin=date_fin,
    ))

    assert response.status_code == 422
    assert client.get("/reservations").json() == []


@pytest.mark.parametrize(
    ("champs", "champ_en_erreur"),
    [
        ({"item_id": 0}, "item_id"),
        ({"date_debut": "pas-une-date"}, "date_debut"),
        ({"statut": "annulee"}, "statut"),   # le client ne choisit pas le statut
    ],
)
def test_creer_reservation_avec_champ_invalide_renvoie_422(
    client: TestClient, champs: dict[str, Any], champ_en_erreur: str
) -> None:
    response = client.post("/reservations", json={**_payload(1), **champs})

    assert response.status_code == 422
    assert champ_en_erreur in [erreur["loc"][-1] for erreur in response.json()["detail"]]


def test_creer_reservation_sans_date_fin_renvoie_422(client: TestClient) -> None:
    payload = _payload(1)
    del payload["date_fin"]

    response = client.post("/reservations", json=payload)

    assert response.status_code == 422
    assert "date_fin" in [erreur["loc"][-1] for erreur in response.json()["detail"]]


# --- GET /reservations -------------------------------------------------------


def test_lister_sans_reservation_renvoie_liste_vide(client: TestClient) -> None:
    response = client.get("/reservations")

    assert response.status_code == 200
    assert response.json() == []


def test_lister_filtre_par_item_id(client: TestClient) -> None:
    client.post("/reservations", json=_payload(1))
    client.post("/reservations", json=_payload(2))
    client.post("/reservations", json=_payload(1, date_debut="2026-10-01", date_fin="2026-10-03"))

    response = client.get("/reservations", params={"item_id": 1})

    assert [r["id"] for r in response.json()] == [1, 3]


def test_lister_avec_limit_tronque_la_liste(client: TestClient) -> None:
    for _ in range(3):
        client.post("/reservations", json=_payload(1))

    response = client.get("/reservations", params={"limit": 2})

    assert [r["id"] for r in response.json()] == [1, 2]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 500}, {"item_id": 0}])
def test_lister_avec_parametre_invalide_renvoie_422(
    client: TestClient, params: dict[str, int]
) -> None:
    response = client.get("/reservations", params=params)

    assert response.status_code == 422


# --- GET /reservations/{reservation_id} --------------------------------------


def test_consulter_reservation_inexistante_renvoie_404(client: TestClient) -> None:
    response = client.get(f"/reservations/{RESERVATION_INEXISTANTE}")

    assert response.status_code == 404
    assert response.json()["detail"] == f"Reservation {RESERVATION_INEXISTANTE} introuvable"


@pytest.mark.parametrize("reservation_id", ["abc", "0"])
def test_consulter_reservation_avec_id_invalide_renvoie_422(
    client: TestClient, reservation_id: str
) -> None:
    response = client.get(f"/reservations/{reservation_id}")

    assert response.status_code == 422


# --- POST /reservations/{reservation_id}/annuler -----------------------------


def test_annuler_reservation_passe_le_statut_a_annulee(
    client: TestClient, reservation_active: dict[str, Any], notifier: Mock
) -> None:
    response = client.post(f"/reservations/{reservation_active['id']}/annuler")

    assert response.status_code == 200
    assert response.json() == {**reservation_active, "statut": "annulee"}
    assert client.get(f"/reservations/{reservation_active['id']}").json()["statut"] == "annulee"


def test_annuler_une_reservation_deja_annulee_renvoie_409(
    client: TestClient, reservation_active: dict[str, Any], notifier: Mock
) -> None:
    # Given : la réservation a déjà été annulée.
    client.post(f"/reservations/{reservation_active['id']}/annuler")

    # When : on demande une seconde annulation.
    response = client.post(f"/reservations/{reservation_active['id']}/annuler")

    # Then : l'API refuse avec un conflit, et la réservation reste annulée.
    assert response.status_code == 409
    assert response.json()["reservation_id"] == reservation_active["id"]
    assert client.get(f"/reservations/{reservation_active['id']}").json()["statut"] == "annulee"


def test_annuler_reservation_inexistante_renvoie_404(client: TestClient, notifier: Mock) -> None:
    response = client.post(f"/reservations/{RESERVATION_INEXISTANTE}/annuler")

    assert response.status_code == 404
    notifier.assert_not_called()


# --- Notification d'annulation (mock) ----------------------------------------


def test_annulation_envoie_une_notification(
    client: TestClient, reservation_active: dict[str, Any], notifier: Mock
) -> None:
    response = client.post(f"/reservations/{reservation_active['id']}/annuler")

    assert response.status_code == 200
    notifier.assert_called_once_with(reservation_id=reservation_active["id"])


def test_double_annulation_ne_notifie_qu_une_fois(
    client: TestClient, reservation_active: dict[str, Any], notifier: Mock
) -> None:
    client.post(f"/reservations/{reservation_active['id']}/annuler")
    client.post(f"/reservations/{reservation_active['id']}/annuler")

    notifier.assert_called_once()


def test_annulation_reussit_meme_si_la_notification_echoue(
    client: TestClient, reservation_active: dict[str, Any], notifier: Mock
) -> None:
    notifier.side_effect = ConnectionError("serveur mail injoignable")

    response = client.post(f"/reservations/{reservation_active['id']}/annuler")

    assert response.status_code == 200
    assert client.get(f"/reservations/{reservation_active['id']}").json()["statut"] == "annulee"
