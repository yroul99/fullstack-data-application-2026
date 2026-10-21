from typing import Any


class ApiError(Exception):
    """Erreur renvoyée par le backend, ou backend injoignable."""

    def __init__(self, status_code: int, detail: Any) -> None:
        super().__init__(f"{status_code}: {detail}")
        self.status_code = status_code
        self.detail = detail
