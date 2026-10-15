from urllib.parse import quote

from django.conf import settings
from django.utils.translation import gettext as _

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
        _("Bonjour, je souhaite connaître les méthodes de paiement pour la conférence.")
    )
    return {
        'whatsapp_contact_number': number,
        'whatsapp_contact_url': f'https://wa.me/{digits}?text={message}',
    }


def footer_contact(request):
    conference = get_active_conference()

    return {
        'footer_conference': conference,
        'footer_contact_address': (
            conference.contact_address if conference and conference.contact_address
            else 'Kinshasa, RDC'
        ),
        'footer_contact_phone': (
            conference.contact_phone if conference and conference.contact_phone
            else '+243986698720'
        ),
        'footer_contact_email': (
            conference.contact_email if conference and conference.contact_email
            else 'bantondosgeneration@gmail.com'
        ),
        'footer_social_facebook': conference.social_facebook if conference else '',
        'footer_social_facebook_label': 'BG/Absl',
        'footer_social_instagram': conference.social_instagram if conference else '',
        'footer_social_instagram_label': 'BG/Asbl',
        'footer_social_twitter': conference.social_twitter if conference else '',
        'footer_social_twitter_label': "@Bantondo'sGeneration",
        'footer_social_tiktok': conference.social_tiktok if conference else '',
        'footer_social_tiktok_label': "Bantondo's Generation",
        'footer_social_linkedin': conference.social_linkedin if conference else '',
        'footer_social_youtube': conference.social_youtube if conference else '',
    }
