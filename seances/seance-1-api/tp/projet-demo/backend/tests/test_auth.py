import pytest
from fastapi.testclient import TestClient

from app.models import User

ALICE = {"email": "alice@esiee.fr", "password": "motdepasse-alice", "display_name": "Alice"}


@pytest.fixture
def alice_inscrite(client: TestClient) -> dict[str, str]:
    """Alice inscrite par l'API, donc avec un vrai condensat de mot de passe."""
    assert client.post("/auth/register", json=ALICE).status_code == 201
    return ALICE


# --- POST /auth/register -----------------------------------------------------


def test_inscription_renvoie_201_sans_mot_de_passe(client: TestClient) -> None:
    response = client.post("/auth/register", json=ALICE)

    assert response.status_code == 201
    corps = response.json()
    assert corps["email"] == "alice@esiee.fr"
    assert corps["display_name"] == "Alice"
    assert "password" not in corps
    assert "password_hash" not in corps


def test_inscription_avec_un_email_deja_utilise_renvoie_409(
    client: TestClient, alice_inscrite: dict[str, str]
) -> None:
    response = client.post("/auth/register", json=ALICE)

    assert response.status_code == 409


@pytest.mark.parametrize(
    ("champs", "champ_en_erreur"),
    [
        ({"email": "pas-un-email"}, "email"),
        ({"password": "abcd"}, "password"),
        ({"password": "a" * 200}, "password"),
    ],
    ids=["email-invalide", "mot-de-passe-4", "mot-de-passe-200"],
)
def test_inscription_invalide_renvoie_422(
    client: TestClient, champs: dict[str, str], champ_en_erreur: str
) -> None:
    response = client.post("/auth/register", json={**ALICE, **champs})

    assert response.status_code == 422
    assert champ_en_erreur in [erreur["loc"][-1] for erreur in response.json()["detail"]]


# --- POST /auth/login --------------------------------------------------------


def test_login_renvoie_un_jeton(client: TestClient, alice_inscrite: dict[str, str]) -> None:
    response = client.post("/auth/login", data={
        "username": alice_inscrite["email"], "password": alice_inscrite["password"],
    })

    assert response.status_code == 200
    corps = response.json()
    assert corps["token_type"] == "bearer"
    assert corps["expires_in"] == 3600
    assert corps["access_token"].count(".") == 2


@pytest.mark.parametrize(
    ("email", "password"),
    [("alice@esiee.fr", "mauvais-mot-de-passe"), ("personne@esiee.fr", "motdepasse-alice")],
    ids=["mauvais-mot-de-passe", "email-inexistant"],
)
def test_login_en_echec_renvoie_toujours_le_meme_401(
    client: TestClient, alice_inscrite: dict[str, str], email: str, password: str
) -> None:
    response = client.post("/auth/login", data={"username": email, "password": password})

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {"detail": "Email ou mot de passe incorrect"}


def test_login_avec_un_condensat_malforme_renvoie_401(client: TestClient, alice: User) -> None:
    # La fixture `alice` a un password_hash factice ("x") : la connexion échoue proprement.
    response = client.post("/auth/login", data={"username": "alice@esiee.fr", "password": "x"})

    assert response.status_code == 401


def test_le_jeton_du_login_donne_acces_a_me(client: TestClient, alice_inscrite: dict[str, str]) -> None:
    jeton = client.post("/auth/login", data={
        "username": alice_inscrite["email"], "password": alice_inscrite["password"],
    }).json()["access_token"]

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {jeton}"})

    assert response.status_code == 200
    assert response.json()["email"] == "alice@esiee.fr"


# --- get_current_user : même 401 quelle que soit la cause ---------------------


@pytest.mark.parametrize(
    "headers",
    [{}, {"Authorization": "Bearer nimportequoi"}, {"Authorization": "Basic YWxpY2U6eA=="}],
    ids=["sans-jeton", "jeton-bidon", "mauvais-schema"],
)
def test_jeton_absent_ou_invalide_renvoie_le_meme_401(
    client: TestClient, headers: dict[str, str]
) -> None:
    response = client.get("/auth/me", headers=headers)

    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"
    assert response.json() == {"detail": "Identifiants invalides"}


def test_jeton_d_un_utilisateur_supprime_renvoie_401(
    client: TestClient, client_carol: TestClient, carol: User, db
) -> None:
    db.delete(carol)
    db.flush()

    response = client_carol.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Identifiants invalides"}
