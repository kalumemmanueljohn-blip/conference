"""
Service centralisé d'envoi d'emails transactionnels.
"""
import logging

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags

logger = logging.getLogger('notifications')


def _send_email(subject, template_name, context, recipient_list, reply_to=None):
    """Fonction générique d'envoi d'email."""
    if not recipient_list:
        logger.warning("Aucun destinataire pour l'email")
        return False

    recipient_list = [e for e in recipient_list if e]
    if not recipient_list:
        return False

    try:
        html_content = render_to_string(f'notifications/emails/{template_name}.html', context)
        text_content = strip_tags(html_content)

        email = EmailMultiAlternatives(
            subject=subject,
            body=text_content,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=recipient_list,
            reply_to=reply_to or [settings.DEFAULT_FROM_EMAIL],
        )
        email.attach_alternative(html_content, "text/html")
        email.send(fail_silently=False)

        logger.info(f"Email '{subject}' envoyé à {recipient_list}")
        return True

    except Exception as e:
        logger.error(f"Erreur envoi email '{subject}' : {e}")
        return False


# ============================================================
# EMAILS PUBLICS
# ============================================================

def send_welcome_email(user):
    """Email de bienvenue après création de compte."""
    return _send_email(
        subject="Bienvenue chez Bantondo's Génération ASBL",
        template_name='welcome',
        context={
            'user': user,
            'login_url': f"{settings.SITE_URL}/compte/connexion/" if hasattr(settings, 'SITE_URL') else None,
        },
        recipient_list=[user.email],
    )


def send_reservation_created_email(reservation):
    """Email après création d'une réservation."""
    return _send_email(
        subject=f"Réservation enregistrée : {reservation.reference}",
        template_name='reservation_created',
        context={
            'user': reservation.user,
            'reservation': reservation,
            'conference': reservation.conference,
        },
        recipient_list=[reservation.user.email],
    )


def send_payment_confirmed_email(payment):
    """Email après confirmation du paiement."""
    return _send_email(
        subject=f"Paiement confirmé — {payment.reservation.reference}",
        template_name='payment_confirmed',
        context={
            'user': payment.reservation.user,
            'reservation': payment.reservation,
            'payment': payment,
            'conference': payment.reservation.conference,
        },
        recipient_list=[payment.reservation.user.email],
    )


def send_whatsapp_validated_email(proof):
    """Email après validation manuelle d'un paiement WhatsApp."""
    return _send_email(
        subject=f"Paiement WhatsApp validé — {proof.payment.reservation.reference}",
        template_name='whatsapp_validated',
        context={
            'user': proof.payment.reservation.user,
            'reservation': proof.payment.reservation,
            'payment': proof.payment,
            'conference': proof.payment.reservation.conference,
        },
        recipient_list=[proof.payment.reservation.user.email],
    )


def send_whatsapp_rejected_email(proof):
    """Email après rejet d'un paiement WhatsApp."""
    return _send_email(
        subject=f"Preuve de paiement rejetée — {proof.payment.reservation.reference}",
        template_name='whatsapp_rejected',
        context={
            'user': proof.payment.reservation.user,
            'reservation': proof.payment.reservation,
            'payment': proof.payment,
            'reason': proof.rejection_reason,
        },
        recipient_list=[proof.payment.reservation.user.email],
    )


def send_ticket_ready_email(reservation):
    """Email quand les billets sont disponibles."""
    return _send_email(
        subject=f"Vos billets sont prêts — {reservation.reference}",
        template_name='ticket_ready',
        context={
            'user': reservation.user,
            'reservation': reservation,
            'tickets': reservation.tickets.all(),
            'conference': reservation.conference,
        },
        recipient_list=[reservation.user.email],
    )


# ============================================================
# WHATSAPP — Message pour envoi manuel
# ============================================================

def prepare_whatsapp_ticket_message(reservation, request=None):
    """
    Prépare le message WhatsApp de confirmation avec le lien de téléchargement.

    Retourne un dict avec :
    - number : numéro WhatsApp du client
    - clean_number : numéro sans +
    - message : message complet (avec sauts de ligne réels)
    - url : lien wa.me prêt à cliquer (message correctement encodé)
    """
    from urllib.parse import quote

    user_number = reservation.user.whatsapp_number
    if not user_number:
        logger.warning(f"Numéro WhatsApp manquant pour {reservation.reference}")
        return None

    # Lien vers la page de téléchargement des billets
    tickets_path = f"/billets/reservation/{reservation.reference}/"
    if request:
        tickets_url = request.build_absolute_uri(tickets_path)
    else:
        tickets_url = f"http://127.0.0.1:8000{tickets_path}"

    # Récupérer le nombre de billets
    total_tickets = reservation.tickets.count() or reservation.seats

    # Date de la conférence
    conference_date = reservation.conference.date.strftime("%d/%m/%Y à %Hh%M")
    conference_location = reservation.conference.location

    # ============================================================
    # MESSAGE WHATSAPP (nouvelle version améliorée)
    # ============================================================
    message = (
        f"Bonjour {reservation.user.first_name},\n"
        f"\n"
        f"Votre paiement a bien ete valide pour la conference.\n"
        f"\n"
        f"REFERENCE : {reservation.reference}\n"
        f"Places reservees : {reservation.seats}\n"
        f"Billets : {total_tickets} au total\n"
        f"\n"
        f"CONFERENCE :\n"
        f"{reservation.conference.title}\n"
        f"\n"
        f"Date : {conference_date}\n"
        f"Lieu : {conference_location}\n"
        f"\n"
        f"Pour telecharger vos billets au format PDF, cliquez sur ce lien :\n"
        f"{tickets_url}\n"
        f"\n"
        f"Comment utiliser votre billet :\n"
        f"1. Telechargez vos billets PDF sur le lien ci-dessus\n"
        f"2. Imprimez-les ou gardez-les sur votre telephone\n"
        f"3. Presentez le QR code a l'entree de la salle\n"
        f"\n"
        f"Important : chaque billet est personnel et valable pour une seule entree. Ne partagez pas votre QR code.\n"
        f"\n"
        f"Merci de votre confiance et a bientot !\n"
        f"\n"
        f"Bantondo's Generation ASBL\n"
        f"Organisation dediee a l'autonomisation des jeunes en RDC"
    )

    clean_number = user_number.replace('+', '').replace(' ', '')

    return {
        'number': user_number,
        'clean_number': clean_number,
        'message': message,
        'url': f"https://wa.me/{clean_number}?text={quote(message)}",
    }


def prepare_whatsapp_rejection_message(proof, request=None):
    """
    Prépare le message WhatsApp de rejet du paiement.

    Retourne un dict avec :
    - number : numéro WhatsApp du client
    - message : message complet
    - url : lien wa.me prêt à cliquer
    """
    from urllib.parse import quote

    reservation = proof.payment.reservation
    user_number = reservation.user.whatsapp_number

    if not user_number:
        return None

    reason = proof.rejection_reason or "Preuve non conforme"

    message = (
        f"Bonjour {reservation.user.first_name},\n"
        f"\n"
        f"Nous n'avons pas pu valider votre paiement pour la reservation {reservation.reference}.\n"
        f"\n"
        f"Motif : {reason}\n"
        f"\n"
        f"Pour resoudre ce probleme, merci de nous envoyer :\n"
        f"- Une capture d'ecran claire et lisible du paiement\n"
        f"- Ou un recu officiel\n"
        f"\n"
        f"Votre place reste reservee en attendant. Des que nous recevons une preuve valide, nous validerons votre reservation.\n"
        f"\n"
        f"Merci de votre comprehension.\n"
        f"\n"
        f"Bantondo's Generation ASBL"
    )

    clean_number = user_number.replace('+', '').replace(' ', '')

    return {
        'number': user_number,
        'clean_number': clean_number,
        'message': message,
        'url': f"https://wa.me/{clean_number}?text={quote(message)}",
    }