from datetime import date

from app.core.exceptions import AccesRefuse, ConflitReservation, RessourceIntrouvable
from app.models.reservation import Reservation
from app.repositories.item import ItemRepository
from app.repositories.reservation import ReservationRepository


class ReservationService:
    def __init__(
        self,
        reservations: ReservationRepository,
        items: ItemRepository,
    ) -> None:
        self.reservations = reservations
        self.items = items

    def get(self, reservation_id: int) -> Reservation:
        reservation = self.reservations.get(reservation_id)
        if reservation is None:
            raise RessourceIntrouvable(f"Réservation {reservation_id} introuvable")
        return reservation

    def list_reservations(self, *, item_id: int | None = None, skip: int = 0, limit: int = 20) -> list[Reservation]:
        return self.reservations.list_reservations(item_id=item_id, skip=skip, limit=limit)

    def creer(self, *, item_id: int, borrower_id: int, debut: date, fin: date) -> Reservation:
        item = self.items.get(item_id)
        if item is None:
            raise RessourceIntrouvable(f"Item {item_id} introuvable")
        if item.owner_id == borrower_id:
            raise ConflitReservation("Vous ne pouvez pas réserver votre propre matériel")
        if not item.disponible:
            raise ConflitReservation("Ce matériel n'est pas disponible")
        if self.reservations.find_chevauchements(item_id, debut, fin):
            raise ConflitReservation("Ce créneau est déjà réservé")

        return self.reservations.add(
            Reservation(item_id=item_id, borrower_id=borrower_id,
                        date_debut=debut, date_fin=fin, statut="active")
        )

    def annuler(self, reservation_id: int, *, current_user_id: int) -> Reservation:
        reservation = self.get(reservation_id)
        if current_user_id not in (reservation.borrower_id, reservation.item.owner_id):
            raise AccesRefuse("Seuls l'emprunteur et le propriétaire peuvent annuler cette réservation")
        if reservation.statut != "active":
            raise ConflitReservation("Seule une réservation active peut être annulée")
        reservation.statut = "annulee"
        return self.reservations.add(reservation)
