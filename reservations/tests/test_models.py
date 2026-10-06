from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from reservations.models import Reservation

User = get_user_model()


@pytest.fixture
def user(db):
    return User.objects.create_user(
        email='jean@example.com', password='SecurePass123',
        first_name='Jean', last_name='Kabila', postnom='Mwamba',
        whatsapp_number='+243812345678',
    )


@pytest.fixture
def conference(db):
    return Conference.objects.create(
        title="Conférence test",
        date=timezone.now() + timedelta(days=30),
        location="Lieu test",
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )


@pytest.mark.django_db
class TestReservationModel:

    def test_generate_reference_format(self):
        ref = Reservation.generate_reference()
        assert ref.startswith('BGA-')
        year = timezone.now().year
        assert f'-{year}-' in ref
        assert len(ref) == 17   # BGA-2026-XXXXXXXX

    def test_compute_total_amount(self, user, conference):
        reservation = Reservation.objects.create(
            reference=Reservation.generate_reference(),
            user=user,
            conference=conference,
            seats=3,
        )
        assert reservation.compute_total_amount() == Decimal('17.10')

    def test_compute_total_amount_free_conference(self, user, conference):
        conference.is_free = True
        conference.save()
        reservation = Reservation.objects.create(
            reference=Reservation.generate_reference(),
            user=user,
            conference=conference,
            seats=3,
        )
        assert reservation.compute_total_amount() == Decimal('0.00')

    def test_mark_as_confirmed(self, user, conference):
        reservation = Reservation.objects.create(
            reference=Reservation.generate_reference(),
            user=user,
            conference=conference,
            seats=2,
        )
        reservation.mark_as_confirmed()
        assert reservation.status == 'confirmed'
        assert reservation.confirmed_at is not None

    def test_mark_as_cancelled(self, user, conference):
        reservation = Reservation.objects.create(
            reference=Reservation.generate_reference(),
            user=user,
            conference=conference,
            seats=1,
        )
        reservation.mark_as_cancelled()
        assert reservation.status == 'cancelled'
        assert reservation.cancelled_at is not None

    def test_is_confirmed_property(self, user, conference):
        reservation = Reservation.objects.create(
            reference=Reservation.generate_reference(),
            user=user,
            conference=conference,
            seats=1,
            status='confirmed',
        )
        assert reservation.is_confirmed is True

    def test_can_be_cancelled(self, user, conference):
        reservation = Reservation.objects.create(
            reference=Reservation.generate_reference(),
            user=user,
            conference=conference,
            seats=1,
            status='created',
        )
        assert reservation.can_be_cancelled is True

        reservation.status = 'confirmed'
        reservation.save()
        assert reservation.can_be_cancelled is False