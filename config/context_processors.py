from email.utils import parseaddr
from urllib.parse import quote

from django.conf import settings

from conference.services import get_active_conference


def get_whatsapp_contact_digits():
    number = settings.WHATSAPP_ADMIN_NUMBER or settings.WHATSAPP_PAYMENT_NUMBER
    digits = ''.join(character for character in number if character.isdigit())
    return digits if 9 <= len(digits) <= 15 else ''


def whatsapp_contact(request):
    number = settings.WHATSAPP_ADMIN_NUMBER or settings.WHATSAPP_PAYMENT_NUMBER
    digits = get_whatsapp_contact_digits()
    if not digits:
        return {
            'whatsapp_contact_number': '',
            'whatsapp_contact_url': '',
        }

    message = quote(
        "Bonjour, je souhaite connaître les méthodes de paiement pour la conférence."
    )
    return {
        'whatsapp_contact_number': number,
        'whatsapp_contact_url': f'https://wa.me/{digits}?text={message}',
    }


def footer_contact(request):
    conference = get_active_conference()
    sender_email = parseaddr(settings.DEFAULT_FROM_EMAIL)[1]

    return {
        'footer_conference': conference,
        'footer_contact_address': (
            conference.contact_address if conference and conference.contact_address
            else 'Kinshasa, RDC'
        ),
        'footer_contact_phone': conference.contact_phone if conference else '',
        'footer_contact_email': (
            conference.contact_email if conference and conference.contact_email
            else sender_email
        ),
        'footer_social_facebook': conference.social_facebook if conference else '',
        'footer_social_instagram': conference.social_instagram if conference else '',
        'footer_social_twitter': conference.social_twitter if conference else '',
        'footer_social_tiktok': conference.social_tiktok if conference else '',
        'footer_social_linkedin': conference.social_linkedin if conference else '',
        'footer_social_youtube': conference.social_youtube if conference else '',
    }
