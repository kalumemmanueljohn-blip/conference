import logging

from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .models import User

logger = logging.getLogger('security')


def send_password_reset_email(user: User, request=None):
    """Envoie l'email de réinitialisation de mot de passe."""
    token = default_token_generator.make_token(user)
    uid = urlsafe_base64_encode(force_bytes(user.pk))

    reset_path = reverse(
        'accounts:password_reset_confirm',
        kwargs={'uidb64': uid, 'token': token},
    )
    reset_url = request.build_absolute_uri(reset_path) if request else reset_path

    subject = "Réinitialisation de votre mot de passe"
    message = render_to_string(
        'accounts/emails/password_reset.txt',
        {'user': user, 'reset_url': reset_url},
    )

    send_mail(
        subject=subject,
        message=message,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
    logger.info(f"Email de reset envoyé à {user.email}")