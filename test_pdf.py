"""
Script de test : génère un PDF à partir de la première réservation confirmée.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from reservations.models import Reservation
from tickets.services import generate_ticket

reservation = Reservation.objects.filter(
    status__in=['confirmed', 'ticket_generated', 'present']
).first()

if not reservation:
    print("Aucune réservation confirmée.")
    print("Créez-en une via l'admin : http://127.0.0.1:8000/admin/")
else:
    print(f"Réservation trouvée : {reservation.reference}")
    ticket = generate_ticket(reservation)
    print(f"Billet généré : {ticket.ticket_reference}")

    if ticket.pdf_file:
        path = ticket.pdf_file.path
        size = os.path.getsize(path)
        print(f"PDF : {path}")
        print(f"Taille : {size} octets")
    else:
        print("ATTENTION : aucun PDF généré")

    if ticket.qr_image:
        print(f"QR : {ticket.qr_image.path}")