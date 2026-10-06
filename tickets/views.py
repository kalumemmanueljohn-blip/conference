import io
import zipfile

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import FileResponse, Http404, HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from .models import Ticket
from .services import get_grouped_pdf_bytes


@login_required
def ticket_detail_view(request, reference):
    """Affiche un billet (uniquement le sien)."""
    ticket = get_object_or_404(
        Ticket.objects.select_related(
            'reservation', 'reservation__conference', 'reservation__user',
        ),
        ticket_reference=reference,
        reservation__user=request.user,
    )

    # Tous les billets de la même réservation
    siblings = ticket.reservation.tickets.order_by('seat_number')

    return render(request, 'tickets/detail.html', {
        'ticket': ticket,
        'siblings': siblings,
    })


@login_required
def reservation_tickets_view(request, reference):
    """
    Affiche tous les billets d'une réservation.
    - Les participants voient uniquement les leurs
    - Les admins (staff) peuvent voir toutes les réservations
    """
    from django.shortcuts import get_object_or_404
    from reservations.models import Reservation

    # Les admins peuvent voir toutes les réservations
    if request.user.is_staff:
        reservation = get_object_or_404(
            Reservation.objects.select_related('conference', 'user'),
            reference=reference,
        )
    else:
        reservation = get_object_or_404(
            Reservation.objects.select_related('conference', 'user'),
            reference=reference,
            user=request.user,
        )

    tickets = reservation.tickets.order_by('seat_number')

    return render(request, 'tickets/reservation_tickets.html', {
        'reservation': reservation,
        'tickets': tickets,
    })


@login_required
def ticket_download_pdf_view(request, reference):
    """Télécharge le PDF d'un billet (uniquement le sien)."""
    ticket = get_object_or_404(
        Ticket,
        ticket_reference=reference,
        reservation__user=request.user,
    )

    if not ticket.pdf_file:
        raise Http404(_("Le PDF n'est pas encore disponible."))

    response = FileResponse(
        ticket.pdf_file.open('rb'),
        content_type='application/pdf',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="{ticket.ticket_reference}.pdf"'
    )
    return response


@login_required
def reservation_pdf_grouped_view(request, reference):
    """Télécharge le PDF groupé de tous les billets d'une réservation."""
    reservation = get_object_or_404(
        request.user.reservations,
        reference=reference,
    )

    if not reservation.tickets.exists():
        messages.error(request, _("Aucun billet n'est disponible."))
        return redirect('reservations:detail', reference=reference)

    try:
        pdf_bytes = get_grouped_pdf_bytes(reservation)
    except Exception as e:
        messages.error(request, f"Erreur génération PDF : {e}")
        return redirect('reservations:detail', reference=reference)

    response = HttpResponse(pdf_bytes, content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="billets-{reservation.reference}.pdf"'
    )
    return response


@login_required
def reservation_zip_view(request, reference):
    """Télécharge un ZIP contenant tous les PDF individuels."""
    reservation = get_object_or_404(
        request.user.reservations,
        reference=reference,
    )

    tickets = reservation.tickets.order_by('seat_number')
    if not tickets.exists():
        messages.error(request, _("Aucun billet n'est disponible."))
        return redirect('reservations:detail', reference=reference)

    # Créer le ZIP en mémoire
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
        for ticket in tickets:
            if ticket.pdf_file:
                with ticket.pdf_file.open('rb') as f:
                    zip_file.writestr(
                        f"{ticket.ticket_reference}.pdf",
                        f.read(),
                    )

    zip_buffer.seek(0)
    response = HttpResponse(
        zip_buffer.read(),
        content_type='application/zip',
    )
    response['Content-Disposition'] = (
        f'attachment; filename="billets-{reservation.reference}.zip"'
    )
    return response