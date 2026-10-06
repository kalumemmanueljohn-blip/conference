"""
Crée des données de test : conférence active + utilisateur + réservation confirmée + billets.
"""
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings.dev')
django.setup()

from decimal import Decimal
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from reservations.models import Reservation
from reservations.services import create_reservation, confirm_reservation
from tickets.services import generate_tickets_for_reservation

User = get_user_model()

# 1. Conférence active
conference = Conference.objects.filter(is_active=True).first()
if not conference:
    print("Création de la conférence...")
    conference = Conference.objects.create(
        title="L'entrepreneuriat des jeunes à Kinshasa, Mythe ou Réalité ?",
        date=timezone.now() + timedelta(days=30),
        location="Auditorium du CHESD GOMBE",
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )
    print(f"Conférence créée : {conference.title}")
else:
    print(f"Conférence existante : {conference.title}")

# 2. Utilisateur
user = User.objects.filter(email='test@example.com').first()
if not user:
    print("Création de l'utilisateur test...")
    user = User.objects.create_user(
        email='test@example.com',
        password='TestPass123',
        first_name='Test',
        last_name='Participant',
        postnom='Mwamba',
        whatsapp_number='+243812345678',
    )
    print(f"Utilisateur créé : {user.email}")
else:
    print(f"Utilisateur existant : {user.email}")

# 3. Réservation
reservation = Reservation.objects.filter(user=user, conference=conference).first()
if not reservation:
    print("Création de la réservation...")
    reservation = create_reservation(user, conference, seats=4)
    confirm_reservation(reservation)
    print(f"Réservation créée : {reservation.reference}")
else:
    print(f"Réservation existante : {reservation.reference} ({reservation.seats} places)")

# 4. Billets + PDF
print("Génération des billets...")
tickets = generate_tickets_for_reservation(reservation)
print(f"{len(tickets)} billet(s) généré(s) :")
for t in tickets:
    print(f"  - {t.ticket_reference} (Place {t.seat_number}/{reservation.seats})")
    if t.pdf_file:
        print(f"    PDF : {t.pdf_file.path}")
        print(f"    Taille : {os.path.getsize(t.pdf_file.path)} octets")

print("\nTerminé.")