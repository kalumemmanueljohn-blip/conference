import logging

from decimal import Decimal

from django.db import transaction
from django.utils import timezone

from conference.models import Conference

from .models import Reservation

logger = logging.getLogger('reservations')

# Constante : nombre maximum de réservations actives par utilisateur
MAX_RESERVATIONS_PER_USER = 5


class ReservationError(Exception):
    """Exception métier pour les réservations."""
    pass


@transaction.atomic
def create_reservation(user, conference: Conference, seats: int,
                       payment_phone_number: str = None) -> Reservation:
    """
    Crée une nouvelle réservation.
    - Vérifie que la conférence accepte des réservations
    - Vérifie qu'il reste assez de places
    - Limite à 5 réservations actives par utilisateur
    - Génère une référence unique
    - Fige le montant total
    """
    # ============================================================
    # 1. Recharger la conférence avec verrou (évite les races)
    # ============================================================
    conference = Conference.objects.select_for_update().get(pk=conference.pk)

    # ============================================================
    # 2. Vérifier que la conférence est active et à venir
    # ============================================================
    if not conference.is_active:
        raise ReservationError("Cette conférence n'est pas active.")

    if conference.is_past:
        raise ReservationError("Cette conférence est déjà passée.")

    # ============================================================
    # 3. Vérifier les places disponibles
    # ============================================================
    if conference.total_seats > 0:
        remaining = conference.seats_remaining

        if remaining <= 0:
            raise ReservationError(
                "Il n'y a plus de places disponibles pour cette conférence."
            )

        if seats > remaining:
            if remaining == 1:
                raise ReservationError(
                    "Il ne reste qu'1 seule place disponible. "
                    "Réduisez le nombre de places."
                )
            raise ReservationError(
                f"Il ne reste que {remaining} places disponibles. "
                f"Réduisez le nombre de places."
            )

    # ============================================================
    # 4. Vérifier la limite de réservations par utilisateur
    # ============================================================
    active_count = Reservation.objects.filter(
        user=user,
        conference=conference,
        status__in=Reservation.ACTIVE_STATUSES,
    ).count()

    if active_count >= MAX_RESERVATIONS_PER_USER:
        raise ReservationError(
            f"Vous avez déjà {MAX_RESERVATIONS_PER_USER} réservations actives "
            f"pour cette conférence. Vous ne pouvez pas en créer d'autres."
        )

    # ============================================================
    # 5. Générer une référence unique
    # ============================================================
    reference = None
    for _ in range(5):
        candidate = Reservation.generate_reference()
        if not Reservation.objects.filter(reference=candidate).exists():
            reference = candidate
            break

    if not reference:
        raise ReservationError(
            "Impossible de générer une référence unique. Réessayez."
        )

    # ============================================================
    # 6. Fallback : si pas de numéro, utiliser le WhatsApp du user
    # ============================================================
    if not payment_phone_number:
        payment_phone_number = user.whatsapp_number

    # ============================================================
    # 7. Créer la réservation
    # ============================================================
    reservation = Reservation.objects.create(
        reference=reference,
        user=user,
        conference=conference,
        seats=seats,
        payment_phone_number=payment_phone_number,
        status='created',
        currency=conference.currency,
    )
    reservation.total_amount = reservation.compute_total_amount()
    reservation.save(update_fields=['total_amount'])

    logger.info(
        f"Réservation créée : {reference} par {user.email} "
        f"({seats} place(s), {reservation.total_amount} USD, "
        f"réservation {active_count + 1}/{MAX_RESERVATIONS_PER_USER})"
    )

    # ============================================================
    # 8. Envoi email (silencieux en cas d'erreur)
    # ============================================================
    try:
        from notifications.services import send_reservation_created_email
        send_reservation_created_email(reservation)
    except Exception as e:
        logger.error(f"Erreur envoi email réservation : {e}")

    return reservation


@transaction.atomic
def confirm_reservation(reservation: Reservation) -> Reservation:
    """Confirme une réservation après validation du paiement."""
    if reservation.status in ['confirmed', 'ticket_generated', 'present']:
        logger.warning(f"Réservation {reservation.reference} déjà confirmée.")
        return reservation

    if reservation.status == 'cancelled':
        raise ReservationError("Impossible de confirmer une réservation annulée.")

    reservation.mark_as_confirmed()
    logger.info(f"Réservation confirmée : {reservation.reference}")
    return reservation


@transaction.atomic
def cancel_reservation(reservation: Reservation, reason: str = "") -> Reservation:
    """Annule une réservation."""
    if not reservation.can_be_cancelled:
        raise ReservationError(
            f"Impossible d'annuler une réservation au statut "
            f"« {reservation.get_status_display()} »."
        )

    reservation.mark_as_cancelled()
    logger.info(f"Réservation annulée : {reservation.reference} — Raison : {reason}")
    return reservation


def get_user_reservations(user):
    """Retourne toutes les réservations d'un utilisateur."""
    return Reservation.objects.filter(user=user).select_related('conference')


def count_user_active_reservations(user, conference: Conference) -> int:
    """Compte les réservations actives d'un utilisateur pour une conférence."""
    return Reservation.objects.filter(
        user=user,
        conference=conference,
        status__in=Reservation.ACTIVE_STATUSES,
    ).count()


def can_user_reserve(user, conference: Conference) -> tuple:
    """
    Vérifie si l'utilisateur peut encore réserver.
    Retourne (bool, message).
    """
    # Vérifier les places disponibles
    if conference.total_seats > 0 and conference.seats_remaining <= 0:
        return (False, "Il n'y a plus de places disponibles pour cette conférence.")

    # Vérifier la limite de réservations
    active_count = count_user_active_reservations(user, conference)
    if active_count >= MAX_RESERVATIONS_PER_USER:
        return (False, f"Vous avez déjà {MAX_RESERVATIONS_PER_USER} réservations actives.")

    return (True, "")