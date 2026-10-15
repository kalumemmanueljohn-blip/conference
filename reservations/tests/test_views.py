from datetime import timedelta
from decimal import Decimal
from tempfile import TemporaryDirectory

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from conference.models import Conference
from reservations.models import Reservation
from tickets.models import Ticket


@override_settings(
    STORAGES={
        'default': {
            'BACKEND': 'django.core.files.storage.FileSystemStorage',
        },
        'staticfiles': {
            'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
        },
    }
)
class CreateReservationViewTests(TestCase):
    def setUp(self):
        self.user = get_user_model().objects.create_user(
            email='participant@example.com',
            password='SecurePass123',
            first_name='Jean',
            last_name='Kabila',
            postnom='Mwamba',
            whatsapp_number='+243812345678',
        )
        self.conference = Conference.objects.create(
            title='Conférence test',
            date=timezone.now() + timedelta(days=30),
            location='Kinshasa',
            price_per_seat=Decimal('5.70'),
            total_seats=100,
            is_active=True,
        )
        self.client.force_login(self.user)

    def test_free_reservation_is_confirmed_and_tickets_are_generated(self):
        self.conference.is_free = True
        self.conference.save(update_fields=['is_free'])

        with TemporaryDirectory() as media_root:
            with override_settings(MEDIA_ROOT=media_root):
                response = self.client.post(
                    reverse('reservations:create'),
                    {'seats': 2},
                )

        reservation = Reservation.objects.get(user=self.user)
        self.assertRedirects(
            response,
            reverse(
                'tickets:reservation_tickets',
                args=[reservation.reference],
            ),
            fetch_redirect_response=False,
        )
        self.assertEqual(reservation.status, 'ticket_generated')
        self.assertEqual(reservation.total_amount, Decimal('0.00'))
        self.assertEqual(Ticket.objects.filter(reservation=reservation).count(), 2)

    def test_paid_reservation_still_requires_payment(self):
        response = self.client.post(
            reverse('reservations:create'),
            {'seats': 1},
        )

        reservation = Reservation.objects.get(user=self.user)
        self.assertRedirects(
            response,
            reverse('reservations:detail', args=[reservation.reference]),
            fetch_redirect_response=False,
        )
        self.assertEqual(reservation.status, 'created')
        self.assertFalse(Ticket.objects.filter(reservation=reservation).exists())
