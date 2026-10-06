import logging

from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from reservations.models import Reservation
from reservations.services import confirm_reservation

from .models import Payment, SaspayTransaction, WhatsappProof
from .saspay import SaspayClient, SaspayError

logger = logging.getLogger('payments')


class PaymentError(Exception):
    """Exception métier paiement."""
    pass


# ============================================================
# SASPAY
# ============================================================

@transaction.atomic
def initiate_saspay_payment(reservation: Reservation) -> Payment:
    """
    Initie un paiement SASPAY.
    Crée Payment + SaspayTransaction, passe la réservation en payment_pending.
    """
    if reservation.status not in ['created', 'payment_pending']:
        raise PaymentError(
            f"Impossible d'initier un paiement sur une réservation "
            f"au statut « {reservation.get_status_display()} »."
        )

    # Vérifier qu'il n'y a pas déjà un paiement SASPAY en cours
    existing = Payment.objects.filter(
        reservation=reservation,
        method='saspay',
        status='pending',
    ).first()
    if existing:
        return existing

    # Créer le paiement
    payment = Payment.objects.create(
        reservation=reservation,
        method='saspay',
        status='pending',
        amount=reservation.total_amount,
        currency=reservation.currency,
        internal_reference=Payment.generate_internal_reference(),
    )

    # Créer la transaction SASPAY
    saspay_tx = SaspayTransaction.objects.create(payment=payment)

    # Appel API SASPAY
    try:
        client = SaspayClient()
        response = client.create_transaction(reservation, payment)

        saspay_tx.raw_request = {
            'reservation_reference': reservation.reference,
            'amount': str(payment.amount),
            'currency': payment.currency,
        }
        saspay_tx.raw_response = response
        saspay_tx.saspay_transaction_id = response.get('transaction_id')  # À compléter
        saspay_tx.saspay_reference = response.get('reference')            # À compléter
        saspay_tx.save()

    except SaspayError as e:
        logger.error(f"Erreur SASPAY : {e}")
        payment.mark_as_rejected()
        raise PaymentError(str(e)) from e

    # Mettre la réservation en attente de paiement
    reservation.mark_as_payment_pending(method='saspay')

    logger.info(f"Paiement SASPAY initié : {payment.internal_reference}")
    return payment


@transaction.atomic
def handle_saspay_webhook(payload: dict, signature: str, raw_body: bytes) -> bool:
    """
    Traite un webhook SASPAY.
    Retourne True si traité (ou déjà traité), False si rejeté.
    """
    client = SaspayClient()

    # 1. Vérifier la signature
    if not client.verify_webhook_signature(raw_body, signature):
        logger.warning("Webhook SASPAY : signature invalide.")
        return False

    # 2. Extraire l'ID de transaction
    transaction_id = payload.get('transaction_id')   # À compléter
    if not transaction_id:
        logger.warning("Webhook SASPAY : transaction_id manquant.")
        return False

    # 3. Idempotence : déjà traité ?
    try:
        saspay_tx = SaspayTransaction.objects.get(saspay_transaction_id=transaction_id)
        if saspay_tx.signature_verified:
            logger.info(f"Webhook SASPAY déjà traité : {transaction_id}")
            return True
    except SaspayTransaction.DoesNotExist:
        logger.warning(f"Webhook SASPAY : transaction inconnue {transaction_id}")
        return False

    # 4. Vérifier côté serveur via API SASPAY
    try:
        verification = client.verify_transaction(transaction_id)
    except SaspayError as e:
        logger.error(f"Erreur vérification SASPAY : {e}")
        return False

    # 5. Contrôles : montant, référence, statut
    # ⚠️ À COMPLÉTER selon la documentation SASPAY
    # if verification.get('status') != 'success':
    #     logger.warning(f"Transaction SASPAY non réussie : {verification}")
    #     return False
    # if Decimal(verification.get('amount')) != saspay_tx.payment.amount:
    #     logger.error(f"Montant SASPAY incorrect pour {transaction_id}")
    #     return False

    # 6. Confirmer
    saspay_tx.signature_verified = True
    saspay_tx.verified_at = timezone.now()
    saspay_tx.raw_response = {**saspay_tx.raw_response, 'verification': verification}
    saspay_tx.save()

    payment = saspay_tx.payment
    payment.mark_as_confirmed()

    reservation = payment.reservation
    reservation.status = 'payment_confirmed'
    reservation.save(update_fields=['status', 'updated_at'])
    confirm_reservation(reservation)

    logger.info(f"Paiement SASPAY confirmé : {payment.internal_reference}")

    # Envoi email de paiement confirmé
    try:
        from notifications.services import send_payment_confirmed_email
        send_payment_confirmed_email(payment)
    except Exception as e:
        logger.error(f"Erreur envoi email paiement SASPAY : {e}")

    return True


# ============================================================
# WHATSAPP
# ============================================================

@transaction.atomic
def initiate_whatsapp_payment(reservation: Reservation) -> Payment:
    """
    Initie un paiement WhatsApp.
    Le paiement reste PENDING jusqu'à validation manuelle admin.
    """
    if reservation.status not in ['created', 'payment_pending']:
        raise PaymentError(
            f"Impossible d'initier un paiement sur une réservation "
            f"au statut « {reservation.get_status_display()} »."
        )

    # Réutiliser un paiement pending existant
    existing = Payment.objects.filter(
        reservation=reservation,
        method='whatsapp',
        status='pending',
    ).first()
    if existing:
        return existing

    payment = Payment.objects.create(
        reservation=reservation,
        method='whatsapp',
        status='pending',
        amount=reservation.total_amount,
        currency=reservation.currency,
        internal_reference=Payment.generate_internal_reference(),
    )

    reservation.mark_as_payment_pending(method='whatsapp')

    logger.info(f"Paiement WhatsApp initié : {payment.internal_reference}")
    return payment


@transaction.atomic
def submit_whatsapp_proof(payment: Payment, proof_file) -> WhatsappProof:
    """Enregistre la preuve WhatsApp envoyée par le participant."""
    if payment.method != 'whatsapp':
        raise PaymentError("Ce paiement n'est pas de type WhatsApp.")
    if payment.status != 'pending':
        raise PaymentError("Ce paiement n'est plus en attente.")

    # Une seule preuve active à la fois
    WhatsappProof.objects.filter(payment=payment, status='pending').delete()

    proof = WhatsappProof.objects.create(
        payment=payment,
        proof_file=proof_file,
        status='pending',
    )
    logger.info(f"Preuve WhatsApp soumise : {payment.internal_reference}")
    return proof

@transaction.atomic
def validate_whatsapp_payment(proof: WhatsappProof, admin_user) -> Payment:
    """Valide manuellement une preuve WhatsApp → confirme le paiement."""
    if proof.status not in ['pending', 'new_proof_requested']:
        raise PaymentError(
            f"Preuve déjà traitée (statut : {proof.get_status_display()})."
        )

    proof.status = 'validated'
    proof.validated_by = admin_user
    proof.validated_at = timezone.now()
    proof.save()

    payment = proof.payment
    payment.mark_as_confirmed()

    reservation = payment.reservation
    reservation.status = 'payment_confirmed'
    reservation.save(update_fields=['status', 'updated_at'])
    confirm_reservation(reservation)

    logger.info(f"WhatsApp validé par {admin_user.email} : {payment.internal_reference}")

    # 1. Générer les billets PDF
    try:
        from tickets.services import generate_tickets_for_reservation
        generate_tickets_for_reservation(reservation)
    except Exception as e:
        logger.error(f"Erreur génération billets : {e}")

    # 2. Envoyer email de confirmation
    try:
        from notifications.services import send_whatsapp_validated_email
        send_whatsapp_validated_email(proof)
    except Exception as e:
        logger.error(f"Erreur envoi email : {e}")

    # 3. Log du message WhatsApp à envoyer au client (manuel)
    try:
        from notifications.services import send_ticket_whatsapp_link
        send_ticket_whatsapp_link(reservation)
    except Exception as e:
        logger.error(f"Erreur préparation WhatsApp : {e}")

    return payment

@transaction.atomic
def reject_whatsapp_payment(proof: WhatsappProof, admin_user, reason: str) -> Payment:
    """Rejette une preuve WhatsApp."""
    proof.status = 'rejected'
    proof.validated_by = admin_user
    proof.validated_at = timezone.now()
    proof.rejection_reason = reason
    proof.save()

    payment = proof.payment
    payment.mark_as_rejected()

    logger.info(f"WhatsApp rejeté par {admin_user.email} : {payment.internal_reference}")

    # Envoi email WhatsApp rejeté
    try:
        from notifications.services import send_whatsapp_rejected_email
        send_whatsapp_rejected_email(proof)
    except Exception as e:
        logger.error(f"Erreur envoi email WhatsApp rejeté : {e}")

    return payment


@transaction.atomic
def request_new_whatsapp_proof(proof: WhatsappProof, admin_user) -> WhatsappProof:
    """Demande une nouvelle preuve au participant."""
    proof.status = 'new_proof_requested'
    proof.validated_by = admin_user
    proof.validated_at = timezone.now()
    proof.save()

    logger.info(f"Nouvelle preuve demandée : {proof.payment.internal_reference}")
    return proof