from urllib.parse import quote

from django.conf import settings


def whatsapp_contact(request):
    number = settings.WHATSAPP_ADMIN_NUMBER or settings.WHATSAPP_PAYMENT_NUMBER
    digits = ''.join(character for character in number if character.isdigit())

    if not 9 <= len(digits) <= 15:
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
