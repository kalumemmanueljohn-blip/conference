from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from reservations.models import Reservation

from config.context_processors import get_whatsapp_contact_digits

from .services import (
    PaymentError,
    initiate_saspay_payment,
    initiate_whatsapp_payment,
)


@login_required
def choose_payment_view(request, reference):
    """Page de choix de la méthode de paiement."""
    reservation = get_object_or_404(
        Reservation, reference=reference, user=request.user,
    )
    if reservation.is_confirmed:
        return redirect('reservations:detail', reference=reference)

    return render(request, 'payments/choose.html', {'reservation': reservation})


@login_required
def saspay_init_view(request, reference):
    """Initie un paiement SASPAY avec choix du réseau."""
    reservation = get_object_or_404(
        Reservation, reference=reference, user=request.user,
    )

    if request.method == 'POST':
        network = request.POST.get('saspay_network', '').strip()
        allowed = ['vodacom_cd_usd', 'airtel_cd_usd', 'orange_cd_usd']
        if network in allowed:
            reservation.saspay_network = network
            reservation.save(update_fields=['saspay_network', 'updated_at'])

    try:
        payment = initiate_saspay_payment(reservation)
        messages.info(request, _("Demande de paiement envoyée."))
        return render(request, 'payments/saspay_redirect.html', {
            'payment': payment,
            'reservation': reservation,
        })
    except PaymentError as e:
        messages.error(request, str(e))
        return redirect('payments:choose', reference=reference)


@login_required
def whatsapp_init_view(request, reference):
    """Initie un paiement WhatsApp et affiche les instructions."""
    reservation = get_object_or_404(
        Reservation, reference=reference, user=request.user,
    )
    try:
        payment = initiate_whatsapp_payment(reservation)
    except PaymentError as e:
        messages.error(request, str(e))
        return redirect('payments:choose', reference=reference)

    # Message WhatsApp pré-rempli
    whatsapp_message = (
        f"Bonjour, je souhaite payer ma réservation.\n"
        f"Référence : {reservation.reference}\n"
        f"Montant : {payment.amount} {payment.currency}\n"
        f"Nombre de places : {reservation.seats}\n"
        f"Nom : {reservation.user.full_name}\n"
        f"\nMerci de m'envoyer les instructions de paiement."
    )

    return render(request, 'payments/whatsapp_instructions.html', {
        'reservation': reservation,
        'payment': payment,
        'whatsapp_admin_number': get_whatsapp_contact_digits(),
        'whatsapp_message': whatsapp_message,
    })