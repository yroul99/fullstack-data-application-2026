import os
from datetime import date
from typing import Any

import httpx


class ApiError(Exception):
    """Erreur renvoyée par le backend, ou backend injoignable."""

    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail

    def messages(self) -> list[str]:
        """Transforme le detail de l'erreur en liste de messages affichables."""
        if isinstance(self.detail, list):
            return [f"{erreur['loc'][-1]} : {erreur['msg']}" for erreur in self.detail]
        return [str(self.detail)]


class ApiClient:
    """Porte d'entrée unique du frontend vers l'API du backend.

    L'instance est partagée par toutes les requêtes de tous les utilisateurs : le jeton n'y est
    jamais rangé, il est passé en paramètre à chaque appel qui en a besoin.
    """

    def __init__(self, base_url: str, timeout: float = 10) -> None:
        self._http = httpx.Client(base_url=base_url, timeout=timeout)

    def _send(self, method: str, url: str, *, token: str | None = None, **kwargs: Any) -> Any:
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        try:
            response = self._http.request(method, url, headers=headers, **kwargs)
        except httpx.RequestError as exc:
            raise ApiError(503, "Le service est momentanément indisponible.") from exc
        if response.is_error:
            try:
                detail = response.json().get("detail")
            except ValueError:
                detail = response.text
            raise ApiError(response.status_code, detail)
        return response.json() if response.content else None

    def login(self, email: str, password: str) -> dict[str, Any]:
        # formulaire OAuth2 : data= (encodé comme un formulaire), pas json=
        return self._send("POST", "/auth/login", data={"username": email, "password": password})

    def register(self, email: str, password: str, display_name: str) -> dict[str, Any]:
        return self._send(
            "POST",
            "/auth/register",
            json={"email": email, "password": password, "display_name": display_name},
        )

    def list_items(self, limit: int = 20) -> list[dict[str, Any]]:
        return self._send("GET", "/items", params={"limit": limit})

    def get_item(self, item_id: int) -> dict[str, Any]:
        return self._send("GET", f"/items/{item_id}")

    def create_item(self, token: str | None, data: dict[str, Any]) -> dict[str, Any]:
        return self._send("POST", "/items", token=token, json=data)

    def list_reservations(self, token: str | None, item_id: int) -> list[dict[str, Any]]:
        return self._send("GET", "/reservations", token=token, params={"item_id": item_id})

    def create_reservation(
        self, token: str | None, item_id: int, date_debut: date, date_fin: date
    ) -> dict[str, Any]:
        return self._send(
            "POST",
            "/reservations",
            token=token,
            json={"item_id": item_id, "date_debut": date_debut.isoformat(), "date_fin": date_fin.isoformat()},
        )

    def update_reservation(self, token: str | None, reservation_id: int, statut: str) -> dict[str, Any]:
        return self._send(
            "PATCH", f"/reservations/{reservation_id}", token=token, json={"statut": statut}
        )


api_client = ApiClient(base_url=os.environ["API_BASE_URL"])
