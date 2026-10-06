from urllib.parse import quote

from django.conf import settings


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
