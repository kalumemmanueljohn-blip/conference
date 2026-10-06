import logging

from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.translation import gettext_lazy as _

from tickets.models import Ticket
from tickets.services import TicketError, mark_participant_present, validate_ticket

from payments.models import Payment, WhatsappProof
from payments.services import (
    PaymentError,
    reject_whatsapp_payment,
    validate_whatsapp_payment,
)

from .services import (
    get_global_stats,
    get_pending_whatsapp_proofs,
    get_recent_payments,
    get_recent_reservations,
    search_reservations,
    search_tickets,
)

logger = logging.getLogger('dashboard')


# ============================================================
# DASHBOARD HOME
# ============================================================

@staff_member_required
def dashboard_home_view(request):
    """Page d'accueil du dashboard admin avec statistiques."""
    stats = get_global_stats()
    context = {
        'stats': stats,
        'recent_reservations': get_recent_reservations(5),
        'recent_payments': get_recent_payments(5),
        'pending_proofs': get_pending_whatsapp_proofs()[:5],
    }
    return render(request, 'dashboard/home.html', context)


# ============================================================
# RECHERCHE
# ============================================================

@staff_member_required
def dashboard_search_view(request):
    """Recherche globale (réservations + billets)."""
    query = request.GET.get('q', '').strip()
    reservations = search_reservations(query) if query else []
    tickets = search_tickets(query) if query else []

    return render(request, 'dashboard/search.html', {
        'query': query,
        'reservations': reservations,
        'tickets': tickets,
    })


# ============================================================
# CONTRÔLE À L'ENTRÉE
# ============================================================

@staff_member_required
def checkin_view(request):
    """Page de contrôle à l'entrée (recherche + scan)."""
    query = request.GET.get('q', '').strip()
    ticket = None
    error = None

    if query:
        ticket = validate_ticket(query)
        if not ticket:
            error = _("Aucun billet trouvé pour « %(q)s ».") % {'q': query}

    return render(request, 'dashboard/checkin.html', {
        'query': query,
        'ticket': ticket,
        'error': error,
    })


@staff_member_required
def checkin_confirm_view(request, reference):
    """Confirme la présence d'un participant."""
    if request.method != 'POST':
        return redirect('dashboard:checkin')

    ticket = get_object_or_404(Ticket, ticket_reference=reference)

    try:
        mark_participant_present(ticket, request.user)
        messages.success(
            request,
            _("Présence validée pour %(ref)s.") % {'ref': ticket.ticket_reference},
        )
    except TicketError as e:
        messages.error(request, str(e))

    return redirect('dashboard:checkin')


# ============================================================
# VALIDATION WHATSAPP
# ============================================================

@staff_member_required
def whatsapp_proofs_list_view(request):
    """
    Liste des paiements WhatsApp en attente de validation.
    Utilise prepare_whatsapp_ticket_message pour le lien WhatsApp.
    """
    status_filter = request.GET.get('status', 'pending')

    payments_qs = Payment.objects.filter(
        method='whatsapp'
    ).select_related(
        'reservation',
        'reservation__user',
        'reservation__conference',
    ).order_by('-created_at')

    if status_filter == 'pending':
        payments_qs = payments_qs.filter(status='pending')
    elif status_filter == 'confirmed':
        payments_qs = payments_qs.filter(status='confirmed')
    elif status_filter == 'rejected':
        payments_qs = payments_qs.filter(status='rejected')

    # Compteurs
    all_wa = Payment.objects.filter(method='whatsapp')
    counts = {
        'pending': all_wa.filter(status='pending').count(),
        'confirmed': all_wa.filter(status='confirmed').count(),
        'rejected': all_wa.filter(status='rejected').count(),
        'all': all_wa.count(),
    }

    # ============================================================
    # Préparer les liens WhatsApp (via fonction centralisée)
    # ============================================================
    from notifications.services import prepare_whatsapp_ticket_message

    payments = []
    for p in payments_qs:
        user = p.reservation.user
        clean_phone = user.whatsapp_number.replace('+', '').replace(' ', '')
        reservation = p.reservation

        # Lien "Contacter" (WhatsApp vide)
        contact_url = f"https://wa.me/{clean_phone}"

        # Lien "Envoyer le billet" (message pré-rempli via la fonction)
        send_ticket_url = ''
        try:
            wa_info = prepare_whatsapp_ticket_message(reservation, request=request)
            if wa_info:
                send_ticket_url = wa_info['url']
        except Exception as e:
            logger.error(f"Erreur préparation WhatsApp : {e}")

        payments.append({
            'obj': p,
            'contact_url': contact_url,
            'send_ticket_url': send_ticket_url,
        })

    context = {
        'payments': payments,
        'status_filter': status_filter,
        'counts': counts,
    }
    return render(request, 'dashboard/whatsapp_proofs.html', context)


@staff_member_required
def whatsapp_proof_detail_view(request, proof_id):
    """
    Détail d'un paiement WhatsApp avec toutes les actions.
    Inclut le bouton "Envoyer le billet sur WhatsApp" quand confirmé.
    """
    payment = get_object_or_404(
        Payment.objects.select_related(
            'reservation',
            'reservation__user',
            'reservation__conference',
        ),
        id=proof_id,
    )

    user = payment.reservation.user
    clean_phone = user.whatsapp_number.replace('+', '').replace(' ', '')

    proof = WhatsappProof.objects.filter(payment=payment).first()

    # Lien WhatsApp avec message (via fonction centralisée)
    whatsapp_ticket_url = ''
    try:
        from notifications.services import prepare_whatsapp_ticket_message
        wa_info = prepare_whatsapp_ticket_message(payment.reservation, request=request)
        if wa_info:
            whatsapp_ticket_url = wa_info['url']
    except Exception as e:
        logger.error(f"Erreur préparation WhatsApp : {e}")

    context = {
        'payment': payment,
        'proof': proof,
        'reservation': payment.reservation,
        'whatsapp_client_url': f"https://wa.me/{clean_phone}",
        'whatsapp_ticket_url': whatsapp_ticket_url,
    }
    return render(request, 'dashboard/whatsapp_proof_detail.html', context)


@staff_member_required
def whatsapp_proof_validate_view(request, proof_id):
    """
    Valide un paiement WhatsApp.
    Confirme le paiement, génère les billets, envoie l'email.
    """
    if request.method != 'POST':
        return redirect('dashboard:whatsapp_proofs')

    payment = get_object_or_404(Payment, id=proof_id)

    try:
        # 1. Confirmer le paiement
        payment.mark_as_confirmed()

        # 2. Confirmer la réservation
        reservation = payment.reservation
        reservation.status = 'payment_confirmed'
        reservation.save(update_fields=['status', 'updated_at'])

        from reservations.services import confirm_reservation
        confirm_reservation(reservation)

        # 3. Générer les billets PDF
        try:
            from tickets.services import generate_tickets_for_reservation
            generate_tickets_for_reservation(reservation)
            logger.info(f"Billets générés pour {reservation.reference}")
        except Exception as e:
            logger.error(f"Erreur génération billets : {e}")

        # 4. Envoyer email de confirmation
        try:
            from notifications.services import send_payment_confirmed_email
            send_payment_confirmed_email(payment)
        except Exception as e:
            logger.error(f"Erreur envoi email : {e}")

        # 5. Log du message WhatsApp à envoyer
        try:
            from notifications.services import prepare_whatsapp_ticket_message
            wa_info = prepare_whatsapp_ticket_message(reservation, request=request)
            if wa_info:
                print("\n" + "=" * 70)
                print("MESSAGE WHATSAPP A ENVOYER AU CLIENT")
                print("=" * 70)
                print(f"Numero : {wa_info['number']}")
                print(f"Nom    : {reservation.user.full_name}")
                print(f"Reference : {reservation.reference}")
                print("-" * 70)
                print("LIEN A OUVRIR :")
                print(wa_info['url'])
                print("-" * 70)
                print("MESSAGE :")
                print(wa_info['message'])
                print("=" * 70 + "\n")
        except Exception as e:
            print(f"\nERREUR preparation WhatsApp : {e}\n")

        messages.success(
            request,
            _("Paiement confirmé pour %(ref)s. Billets générés et email envoyé.") % {
                'ref': reservation.reference
            },
        )

    except Exception as e:
        logger.error(f"Erreur validation paiement {payment.internal_reference} : {e}")
        messages.error(request, f"Erreur : {e}")

    return redirect('dashboard:whatsapp_proof_detail', proof_id=payment.id)


@staff_member_required
def whatsapp_proof_reject_view(request, proof_id):
    """Rejette un paiement WhatsApp."""
    if request.method != 'POST':
        return redirect('dashboard:whatsapp_proofs')

    payment = get_object_or_404(Payment, id=proof_id)
    reason = request.POST.get('reason', '').strip() or "Paiement non conforme"

    try:
        payment.mark_as_rejected()

        proof = WhatsappProof.objects.filter(payment=payment).first()
        if proof:
            from django.utils import timezone
            proof.status = 'rejected'
            proof.validated_by = request.user
            proof.validated_at = timezone.now()
            proof.rejection_reason = reason
            proof.save()

        logger.info(
            f"Paiement WhatsApp rejeté par {request.user.email} : "
            f"{payment.internal_reference} — Raison : {reason}"
        )

        messages.warning(
            request,
            _("Paiement rejeté pour %(ref)s.") % {
                'ref': payment.reservation.reference
            },
        )
    except Exception as e:
        logger.error(f"Erreur rejet paiement {payment.internal_reference} : {e}")
        messages.error(request, f"Erreur : {e}")

    return redirect('dashboard:whatsapp_proofs')