"""
Point d'entrée WSGI.
Utilisé par Gunicorn en production : gunicorn config.wsgi:application
"""
import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.prod')

application = get_wsgi_application()