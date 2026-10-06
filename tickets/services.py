import logging

from django.core.files.base import ContentFile
from django.db import transaction

from reservations.models import Reservation

from .models import Ticket
from .pdf import generate_ticket_pdf, generate_grouped_pdf
from .qr import generate_qr_image

logger = logging.getLogger('tickets')


class TicketError(Exception):
    """Exception métier billet."""
    pass


def _build_ticket_reference(reservation_reference: str, seat_number: int) -> str:
    """
    Ex: BGA-2026-CF792406 + 2  →  BGA-2026-CF792406-02
    """
    return f"{reservation_reference}-{seat_number:02d}"


@transaction.atomic
def generate_tickets_for_reservation(reservation: Reservation):
    """
    Génère N billets pour une réservation de N places.
    Idempotent : régénère les billets s'ils existent déjà.
    """
    if not reservation.is_confirmed:
        raise TicketError(
            f"Impossible de générer les billets pour une réservation "
            f"au statut « {reservation.get_status_display()} »."
        )

    # Supprimer les anciens billets de cette réservation
    Ticket.objects.filter(reservation=reservation).delete()

    created_tickets = []

    for seat_num in range(1, reservation.seats + 1):
        reference = _build_ticket_reference(reservation.reference, seat_num)
        qr_token = Ticket.generate_qr_token(reference)

        ticket = Ticket.objects.create(
            reservation=reservation,
            ticket_reference=reference,
            seat_number=seat_num,
            qr_token=qr_token,
        )

        # QR image
        qr_image = generate_qr_image(qr_token)
        ticket.qr_image.save(f"{reference}.png", qr_image, save=False)

        # PDF individuel
        try:
            pdf_bytes = generate_ticket_pdf(ticket)
            ticket.pdf_file.save(
                f"{reference}.pdf",
                ContentFile(pdf_bytes),
                save=False,
            )
        except Exception as e:
            logger.error(f"Erreur PDF individuel {reference} : {e}")

        ticket.save()
        created_tickets.append(ticket)

    # Mettre à jour le statut
    if reservation.status != 'ticket_generated':
        reservation.status = 'ticket_generated'
        reservation.save(update_fields=['status', 'updated_at'])

    logger.info(
        f"{len(created_tickets)} billet(s) généré(s) "
        f"pour {reservation.reference}"
    )
    # Envoi email billets prêts
    try:
        from notifications.services import send_ticket_ready_email
        send_ticket_ready_email(reservation)
    except Exception as e:
        logger.error(f"Erreur envoi email billets : {e}")

    return created_tickets


# Alias pour compatibilité avec le code existant
generate_ticket = generate_tickets_for_reservation


@transaction.atomic
def validate_ticket(token_or_reference: str):
    """Recherche un billet par QR token OU référence."""
    if '.' in token_or_reference:
        reference = Ticket.verify_qr_token(token_or_reference)
        if reference is None:
            return None
        return Ticket.objects.filter(ticket_reference=reference).first()

    return Ticket.objects.filter(ticket_reference=token_or_reference).first()


@transaction.atomic
def mark_participant_present(ticket: Ticket, admin_user) -> Ticket:
    """Marque un billet comme utilisé. Bloque la réutilisation."""
    ticket = Ticket.objects.select_for_update().get(pk=ticket.pk)

    if ticket.status == 'used':
        raise TicketError(
            f"Billet déjà utilisé le {ticket.used_at.strftime('%d/%m/%Y %H:%M')}."
        )
    if ticket.status == 'cancelled':
        raise TicketError("Billet annulé.")

    ticket.mark_as_used(admin_user)

    # Vérifier si TOUS les billets de la réservation sont utilisés
    reservation = ticket.reservation
    remaining = reservation.tickets.exclude(status='used').exclude(status='cancelled').count()
    if remaining == 0:
        reservation.status = 'present'
        reservation.save(update_fields=['status', 'updated_at'])

    logger.info(
        f"Présence validée : {ticket.ticket_reference} "
        f"par {admin_user.email}"
    )
    return ticket


def get_grouped_pdf_bytes(reservation: Reservation) -> bytes:
    """
    Génère le PDF groupé (N billets dans un seul fichier).
    """
    return generate_grouped_pdf(reservation)