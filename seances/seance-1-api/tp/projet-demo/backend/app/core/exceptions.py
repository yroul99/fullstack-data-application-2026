"""Exceptions métier de l'application.

Aucune ne connaît HTTP : un service peut les lever sans savoir qu'il est appelé par une route.
La traduction en code HTTP est faite une seule fois, par le gestionnaire déclaré dans `main.py`.
"""


class DomainError(Exception):
    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class RessourceIntrouvable(DomainError): ...
class ConflitReservation(DomainError): ...
class AccesRefuse(DomainError): ...
class EmailDejaUtilise(DomainError): ...
