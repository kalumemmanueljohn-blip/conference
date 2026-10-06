from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from conference.models import Conference
from conference.services import get_active_conference

from .forms import ReservationForm
from .models import Reservation
from .services import (
    MAX_RESERVATIONS_PER_USER,
    ReservationError,
    cancel_reservation,
    count_user_active_reservations,
    create_reservation,
)


@login_required
def create_reservation_view(request):
    """Créer une nouvelle réservation pour la conférence active."""
    conference = get_active_conference()

    if not conference:
        messages.error(request, _("Aucune conférence active pour le moment."))
        return redirect('conference:home')

    # Vérifier les places disponibles AVANT d'afficher le formulaire
    if conference.total_seats > 0 and conference.seats_remaining <= 0:
        messages.error(
            request,
            _("Il n'y a plus de places disponibles pour cette conférence."),
        )
        return redirect('conference:home')

    # Vérifier la limite de réservations
    active_count = count_user_active_reservations(request.user, conference)
    if active_count >= MAX_RESERVATIONS_PER_USER:
        messages.error(
            request,
            _("Vous avez déjà %(count)s réservations actives. "
              "Vous ne pouvez pas en créer d'autres.") % {
                'count': MAX_RESERVATIONS_PER_USER
            },
        )
        return redirect('reservations:list')

    # Créer le formulaire
    form = ReservationForm(
        request.POST or None,
        conference=conference,
        user=request.user,
    )

    if request.method == 'POST' and form.is_valid():
        try:
            reservation = create_reservation(
                user=request.user,
                conference=conference,
                seats=form.cleaned_data['seats'],
                payment_phone_number=form.cleaned_data['payment_phone_number'],
            )
            messages.success(
                request,
                _("Réservation créée : %(ref)s") % {'ref': reservation.reference},
            )
            return redirect('reservations:detail', reference=reservation.reference)

        except ReservationError as e:
            messages.error(request, str(e))

    # Info pour le template
    places_remaining = None
    if conference.total_seats > 0:
        places_remaining = conference.seats_remaining

    return render(request, 'reservations/create.html', {
        'form': form,
        'conference': conference,
        'user_reservations_count': active_count,
        'max_reservations': MAX_RESERVATIONS_PER_USER,
        'places_remaining': places_remaining,
    })


@login_required
def my_reservations_view(request):
    """Liste des réservations de l'utilisateur connecté."""
    reservations = Reservation.objects.filter(
        user=request.user
    ).select_related('conference').order_by('-created_at')

    return render(request, 'reservations/list.html', {
        'reservations': reservations,
    })


@login_required
def reservation_detail_view(request, reference):
    """Détail d'une réservation (uniquement la sienne)."""
    reservation = get_object_or_404(
        Reservation.objects.select_related('conference'),
        reference=reference,
        user=request.user,
    )

    return render(request, 'reservations/detail.html', {
        'reservation': reservation,
    })


@login_required
def cancel_reservation_view(request, reference):
    """Annuler une réservation."""
    reservation = get_object_or_404(
        Reservation,
        reference=reference,
        user=request.user,
    )

    if request.method == 'POST':
        try:
            cancel_reservation(reservation, reason="Annulation par l'utilisateur")
            messages.success(request, _("Réservation annulée."))
            return redirect('reservations:list')
        except ReservationError as e:
            messages.error(request, str(e))

    return render(request, 'reservations/cancel.html', {
        'reservation': reservation,
    })