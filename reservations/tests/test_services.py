from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from reservations.models import Reservation
from reservations.services import (
    ReservationError,
    cancel_reservation,
    confirm_reservation,
    create_reservation,
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
class TestCreateReservation:

    def test_create_success(self, user, conference):
        reservation = create_reservation(user, conference, seats=2)
        assert reservation.status == 'created'
        assert reservation.seats == 2
        assert reservation.total_amount == Decimal('11.40')
        assert reservation.reference.startswith('BGA-')

    def test_create_inactive_conference(self, user, conference):
        conference.is_active = False
        conference.save()
        with pytest.raises(ReservationError, match="pas active"):
            create_reservation(user, conference, seats=1)

    def test_create_past_conference(self, user, conference):
        conference.date = timezone.now() - timedelta(days=1)
        conference.save()
        with pytest.raises(ReservationError, match="déjà passée"):
            create_reservation(user, conference, seats=1)

    def test_create_duplicate_active_reservation(self, user, conference):
        create_reservation(user, conference, seats=1)
        with pytest.raises(ReservationError, match="déjà une réservation"):
            create_reservation(user, conference, seats=1)

    def test_create_exceeds_seats(self, user, conference):
        """Réserver plus que les places restantes → doit lever une erreur."""
        conference.total_seats = 5
        conference.save()

        # Premier utilisateur réserve 4 places
        create_reservation(user, conference, seats=4)

        # Second utilisateur tente 4 places (il n'en reste qu'1)
        user2 = User.objects.create_user(
            email='marie@example.com', password='SecurePass123',
            first_name='Marie', last_name='Kabila', postnom='Mwamba',
            whatsapp_number='+243812345679',
        )
        with pytest.raises(ReservationError, match="place"):
            create_reservation(user2, conference, seats=4)


@pytest.mark.django_db
class TestConfirmReservation:

    def test_confirm_success(self, user, conference):
        reservation = create_reservation(user, conference, seats=1)
        confirmed = confirm_reservation(reservation)
        assert confirmed.status == 'confirmed'
        assert confirmed.confirmed_at is not None

    def test_confirm_already_confirmed(self, user, conference):
        reservation = create_reservation(user, conference, seats=1)
        confirm_reservation(reservation)
        result = confirm_reservation(reservation)   # idempotent
        assert result.status == 'confirmed'

    def test_confirm_cancelled(self, user, conference):
        reservation = create_reservation(user, conference, seats=1)
        reservation.mark_as_cancelled()
        with pytest.raises(ReservationError, match="annulée"):
            confirm_reservation(reservation)


@pytest.mark.django_db
class TestCancelReservation:

    def test_cancel_success(self, user, conference):
        reservation = create_reservation(user, conference, seats=1)
        cancelled = cancel_reservation(reservation, reason="Test")
        assert cancelled.status == 'cancelled'

    def test_cancel_confirmed_fails(self, user, conference):
        reservation = create_reservation(user, conference, seats=1)
        confirm_reservation(reservation)
        with pytest.raises(ReservationError):
            cancel_reservation(reservation)