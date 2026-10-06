from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from reservations.services import create_reservation, confirm_reservation
from tickets.models import Ticket

User = get_user_model()


@pytest.fixture
def confirmed_reservation(db):
    user = User.objects.create_user(
        email='jean@example.com', password='SecurePass123',
        first_name='Jean', last_name='Kabila', postnom='Mwamba',
        whatsapp_number='+243812345678',
    )
    conference = Conference.objects.create(
        title="Conférence test",
        date=timezone.now() + timedelta(days=30),
        location="Lieu test",
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )
    reservation = create_reservation(user, conference, seats=2)
    confirm_reservation(reservation)
    return reservation


@pytest.mark.django_db
class TestTicketModel:

    def test_generate_qr_token_format(self):
        token = Ticket.generate_qr_token('BGA-2026-TEST001')
        assert token.startswith('BGA-2026-TEST001.')
        assert len(token.rsplit('.', 1)[1]) == 16

    def test_verify_qr_token_valid(self):
        token = Ticket.generate_qr_token('BGA-2026-TEST001')
        ref = Ticket.verify_qr_token(token)
        assert ref == 'BGA-2026-TEST001'

    def test_verify_qr_token_invalid_signature(self):
        token = 'BGA-2026-TEST001.0000000000000000'
        ref = Ticket.verify_qr_token(token)
        assert ref is None

    def test_verify_qr_token_malformed(self):
        assert Ticket.verify_qr_token('invalid') is None
        assert Ticket.verify_qr_token('') is None

    def test_create_ticket(self, confirmed_reservation):
        token = Ticket.generate_qr_token(confirmed_reservation.reference)
        ticket = Ticket.objects.create(
            reservation=confirmed_reservation,
            ticket_reference=confirmed_reservation.reference,
            qr_token=token,
        )
        assert ticket.status == 'generated'
        assert ticket.is_usable is True

    def test_mark_as_used(self, confirmed_reservation):
        admin = User.objects.create_superuser(
            email='admin@example.com', password='AdminPass123',
            first_name='Admin', last_name='Root', postnom='Sys',
            whatsapp_number='+243812345678',
        )
        token = Ticket.generate_qr_token(confirmed_reservation.reference)
        ticket = Ticket.objects.create(
            reservation=confirmed_reservation,
            ticket_reference=confirmed_reservation.reference,
            qr_token=token,
        )
        ticket.mark_as_used(admin)
        assert ticket.status == 'used'
        assert ticket.used_at is not None
        assert ticket.checked_by == admin