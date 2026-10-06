from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from dashboard.services import (
    get_global_stats,
    search_reservations,
    search_tickets,
)
from payments.services import (
    initiate_whatsapp_payment,
    submit_whatsapp_proof,
    validate_whatsapp_payment,
)
from reservations.services import create_reservation
from tickets.services import generate_ticket

User = get_user_model()


@pytest.fixture
def active_conference(db):
    return Conference.objects.create(
        title="Conférence test active",
        date=timezone.now() + timedelta(days=30),
        location="Lieu",
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='jean@example.com', password='SecurePass123',
        first_name='Jean', last_name='Kabila', postnom='Mwamba',
        whatsapp_number='+243812345678',
    )


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email='admin@example.com', password='AdminPass123',
        first_name='Admin', last_name='Root', postnom='Sys',
        whatsapp_number='+243812345678',
    )


@pytest.mark.django_db
class TestGlobalStats:

    def test_empty_stats(self):
        stats = get_global_stats()
        assert stats['total_users'] == 0
        assert stats['total_reservations'] == 0
        assert stats['total_revenue'] == Decimal('0.00')

    def test_stats_with_reservation(self, user, active_conference):
        create_reservation(user, active_conference, seats=2)
        stats = get_global_stats()
        assert stats['total_reservations'] == 1
        assert stats['seats_reserved'] == 2

    def test_stats_after_confirmation(self, user, active_conference, admin_user):
        reservation = create_reservation(user, active_conference, seats=1)
        payment = initiate_whatsapp_payment(reservation)
        proof = submit_whatsapp_proof(payment, 'proofs/test.jpg')
        validate_whatsapp_payment(proof, admin_user)

        stats = get_global_stats()
        assert stats['confirmed_reservations'] == 1
        assert stats['payments_confirmed'] == 1
        assert stats['total_revenue'] == Decimal('5.70')


@pytest.mark.django_db
class TestSearch:

    def test_search_reservation_by_reference(self, user, active_conference):
        reservation = create_reservation(user, active_conference, seats=1)
        results = search_reservations(reservation.reference)
        assert reservation in results

    def test_search_reservation_by_email(self, user, active_conference):
        reservation = create_reservation(user, active_conference, seats=1)
        results = search_reservations('jean@example.com')
        assert reservation in results

    def test_search_reservation_empty(self):
        assert search_reservations('').count() == 0

    def test_search_ticket(self, user, active_conference, admin_user):
        reservation = create_reservation(user, active_conference, seats=1)
        payment = initiate_whatsapp_payment(reservation)
        proof = submit_whatsapp_proof(payment, 'proofs/test.jpg')
        validate_whatsapp_payment(proof, admin_user)
        ticket = generate_ticket(reservation)

        results = search_tickets(ticket.ticket_reference)
        assert ticket in results