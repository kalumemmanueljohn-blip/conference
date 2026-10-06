import logging

from decimal import Decimal

from django.db.models import Count, Q, Sum

from accounts.models import User
from conference.models import Conference
from conference.services import get_active_conference
from payments.models import Payment, WhatsappProof
from reservations.models import Reservation
from tickets.models import Ticket

logger = logging.getLogger('reservations')


def get_global_stats() -> dict:
    """
    Retourne toutes les statistiques du dashboard.
    """
    active_conference = get_active_conference()

    # Base : filtrer sur la conférence active si elle existe
    if active_conference:
        reservations_qs = Reservation.objects.filter(conference=active_conference)
        payments_qs = Payment.objects.filter(reservation__conference=active_conference)
        tickets_qs = Ticket.objects.filter(reservation__conference=active_conference)
    else:
        reservations_qs = Reservation.objects.all()
        payments_qs = Payment.objects.all()
        tickets_qs = Ticket.objects.all()

    # Utilisateurs
    total_users = User.objects.filter(is_participant=True).count()

    # Réservations
    total_reservations = reservations_qs.count()
    confirmed_reservations = reservations_qs.filter(
        status__in=['confirmed', 'ticket_generated', 'present']
    ).count()
    cancelled_reservations = reservations_qs.filter(status='cancelled').count()
    seats_reserved = reservations_qs.filter(
        status__in=['created', 'payment_pending', 'payment_confirmed',
                    'confirmed', 'ticket_generated', 'present']
    ).aggregate(total=Sum('seats'))['total'] or 0

    # Paiements
    payments_confirmed = payments_qs.filter(status='confirmed').count()
    payments_pending = payments_qs.filter(status='pending').count()
    payments_rejected = payments_qs.filter(status='rejected').count()

    # Montants
    total_revenue = payments_qs.filter(status='confirmed').aggregate(
        total=Sum('amount')
    )['total'] or Decimal('0.00')

    # Preuves WhatsApp à traiter
    whatsapp_proofs_pending = WhatsappProof.objects.filter(
        status='pending',
        payment__reservation__conference=active_conference if active_conference else None,
    ).count() if active_conference else WhatsappProof.objects.filter(status='pending').count()

    # Billets
    total_tickets = tickets_qs.count()
    tickets_used = tickets_qs.filter(status='used').count()
    tickets_unused = tickets_qs.filter(status='generated').count()

    # Taux de présence
    presence_rate = 0
    if total_tickets > 0:
        presence_rate = round((tickets_used / total_tickets) * 100, 1)

    # Capacité
    seats_capacity = 0
    seats_remaining = 0
    if active_conference:
        seats_capacity = active_conference.total_seats
        seats_remaining = active_conference.seats_remaining

    return {
        'active_conference': active_conference,
        'total_users': total_users,
        'total_reservations': total_reservations,
        'confirmed_reservations': confirmed_reservations,
        'cancelled_reservations': cancelled_reservations,
        'seats_reserved': seats_reserved,
        'seats_capacity': seats_capacity,
        'seats_remaining': seats_remaining,
        'payments_confirmed': payments_confirmed,
        'payments_pending': payments_pending,
        'payments_rejected': payments_rejected,
        'total_revenue': total_revenue,
        'whatsapp_proofs_pending': whatsapp_proofs_pending,
        'total_tickets': total_tickets,
        'tickets_used': tickets_used,
        'tickets_unused': tickets_unused,
        'presence_rate': presence_rate,
    }


def search_reservations(query: str):
    """
    Recherche multi-champs sur les réservations.
    Champs : référence, nom, postnom, prénom, email, WhatsApp.
    """
    if not query:
        return Reservation.objects.none()

    return Reservation.objects.filter(
        Q(reference__icontains=query) |
        Q(user__first_name__icontains=query) |
        Q(user__last_name__icontains=query) |
        Q(user__postnom__icontains=query) |
        Q(user__email__icontains=query) |
        Q(user__whatsapp_number__icontains=query)
    ).select_related('user', 'conference').order_by('-created_at')


def search_tickets(query: str):
    """
    Recherche multi-champs sur les billets.
    Champs : référence billet, référence réservation, nom, email, WhatsApp.
    """
    if not query:
        return Ticket.objects.none()

    return Ticket.objects.filter(
        Q(ticket_reference__icontains=query) |
        Q(reservation__reference__icontains=query) |
        Q(reservation__user__first_name__icontains=query) |
        Q(reservation__user__last_name__icontains=query) |
        Q(reservation__user__postnom__icontains=query) |
        Q(reservation__user__email__icontains=query) |
        Q(reservation__user__whatsapp_number__icontains=query)
    ).select_related(
        'reservation',
        'reservation__user',
        'reservation__conference',
    ).order_by('-generated_at')


def get_recent_reservations(limit: int = 10):
    """Retourne les N dernières réservations."""
    return Reservation.objects.select_related('user', 'conference').order_by('-created_at')[:limit]


def get_recent_payments(limit: int = 10):
    """Retourne les N derniers paiements."""
    return Payment.objects.select_related(
        'reservation', 'reservation__user'
    ).order_by('-created_at')[:limit]


def get_pending_whatsapp_proofs():
    """Retourne les preuves WhatsApp en attente de validation."""
    return WhatsappProof.objects.filter(
        status='pending'
    ).select_related(
        'payment',
        'payment__reservation',
        'payment__reservation__user',
    ).order_by('uploaded_at')