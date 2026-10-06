from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from reservations.services import create_reservation, confirm_reservation
from tickets.models import Ticket
from tickets.services import (
    TicketError,
    generate_ticket,
    mark_participant_present,
    validate_ticket,
)

User = get_user_model()


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


@pytest.fixture
def confirmed_reservation(db, user):
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
class TestGenerateTicket:

    def test_generate_success(self, confirmed_reservation):
        ticket = generate_ticket(confirmed_reservation)
        assert ticket.ticket_reference == confirmed_reservation.reference
        assert ticket.status == 'generated'
        assert ticket.qr_token
        confirmed_reservation.refresh_from_db()
        assert confirmed_reservation.status == 'ticket_generated'

    def test_generate_idempotent(self, confirmed_reservation):
        t1 = generate_ticket(confirmed_reservation)
        t2 = generate_ticket(confirmed_reservation)
        assert t1.pk == t2.pk

    def test_generate_unconfirmed_fails(self, user):
        conference = Conference.objects.create(
            title="Conférence test",
            date=timezone.now() + timedelta(days=30),
            location="Lieu test",
            price_per_seat=Decimal('5.70'),
            total_seats=100,
            is_active=True,
        )
        reservation = create_reservation(user, conference, seats=1)
        with pytest.raises(TicketError, match="statut"):
            generate_ticket(reservation)


@pytest.mark.django_db
class TestValidateTicket:

    def test_validate_by_reference(self, confirmed_reservation):
        ticket = generate_ticket(confirmed_reservation)
        found = validate_ticket(ticket.ticket_reference)
        assert found == ticket

    def test_validate_by_qr_token(self, confirmed_reservation):
        ticket = generate_ticket(confirmed_reservation)
        found = validate_ticket(ticket.qr_token)
        assert found == ticket

    def test_validate_invalid_token(self):
        assert validate_ticket('BGA-2026-INVALID.0000000000000000') is None
        assert validate_ticket('NONEXISTENT') is None


@pytest.mark.django_db
class TestMarkPresent:

    def test_mark_present_success(self, confirmed_reservation, admin_user):
        ticket = generate_ticket(confirmed_reservation)
        result = mark_participant_present(ticket, admin_user)
        assert result.status == 'used'
        assert result.used_at is not None
        confirmed_reservation.refresh_from_db()
        assert confirmed_reservation.status == 'present'

    def test_mark_present_already_used(self, confirmed_reservation, admin_user):
        ticket = generate_ticket(confirmed_reservation)
        mark_participant_present(ticket, admin_user)
        with pytest.raises(TicketError, match="déjà utilisé"):
            mark_participant_present(ticket, admin_user)

    def test_mark_present_cancelled(self, confirmed_reservation, admin_user):
        ticket = generate_ticket(confirmed_reservation)
        ticket.status = 'cancelled'
        ticket.save()
        with pytest.raises(TicketError, match="annulé"):
            mark_participant_present(ticket, admin_user)