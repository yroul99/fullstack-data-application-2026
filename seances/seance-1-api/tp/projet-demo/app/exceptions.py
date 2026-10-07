"""Exceptions métier de l'application.

Elles ne dépendent pas de FastAPI : un service ou un futur accès base de données
peut les lever sans rien savoir du protocole HTTP. La traduction en réponse HTTP
est faite une seule fois, par les gestionnaires déclarés dans `main.py`.
"""


class ReservationConflict(Exception):
    """Une réservation est dans un état incompatible avec l'action demandée."""

    def __init__(self, reservation_id: int, message: str) -> None:
        self.reservation_id = reservation_id
        self.message = message
        super().__init__(message)
