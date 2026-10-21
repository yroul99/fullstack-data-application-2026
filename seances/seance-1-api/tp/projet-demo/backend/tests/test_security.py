import hashlib
import secrets

import pytest

from app.core.security import ALGORITHM, hash_password, verify_password


def test_deux_hachages_du_meme_mot_de_passe_sont_differents() -> None:
    assert hash_password("motdepasse-alice") != hash_password("motdepasse-alice")


def test_le_bon_mot_de_passe_est_accepte() -> None:
    stored = hash_password("motdepasse-alice")

    assert verify_password("motdepasse-alice", stored) is True


def test_un_mauvais_mot_de_passe_est_refuse() -> None:
    stored = hash_password("motdepasse-alice")

    assert verify_password("motdepasse-bob", stored) is False


@pytest.mark.parametrize(
    "stored",
    ["x", "", "pbkdf2_sha256$abc$00$00", "pbkdf2_sha256$600000$pas-hexa$00", "md5$1$00$00"],
)
def test_un_condensat_malforme_est_refuse_sans_erreur(stored: str) -> None:
    assert verify_password("motdepasse-alice", stored) is False


def test_un_condensat_avec_un_autre_nombre_d_iterations_reste_verifiable() -> None:
    # Given : un condensat produit avec un coût différent de la constante actuelle.
    salt = secrets.token_bytes(16)
    dk = hashlib.pbkdf2_hmac("sha256", b"motdepasse-alice", salt, 1_000)
    stored = f"{ALGORITHM}$1000${salt.hex()}${dk.hex()}"

    # When / Then : le coût est relu dans la chaîne stockée.
    assert verify_password("motdepasse-alice", stored) is True
    assert verify_password("mauvais", stored) is False
