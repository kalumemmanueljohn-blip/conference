"""Configuration développement — SQLite, emails console, pas de HTTPS."""
from .base import *  # noqa

DEBUG = True
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='', cast=Csv())

# Envoi réel via Gmail SMTP
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'

SECURE_SSL_REDIRECT = False
SESSION_COOKIE_SECURE = False
CSRF_COOKIE_SECURE = False
