from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from conference.models import Conference
from reservations.services import confirm_reservation, create_reservation
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
class TicketQrImageViewTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.user = user_model.objects.create_user(
            email='participant@example.com',
            password='SecurePass123',
            first_name='Jean',
            last_name='Kabila',
            postnom='Mwamba',
            whatsapp_number='+243812345678',
        )
        conference = Conference.objects.create(
            title='Conférence test',
            date=timezone.now() + timedelta(days=30),
            location='Kinshasa',
            price_per_seat=Decimal('5.70'),
            total_seats=100,
            is_active=True,
        )
        reservation = create_reservation(self.user, conference, seats=1)
        confirm_reservation(reservation)
        reference = f'{reservation.reference}-01'
        self.ticket = Ticket.objects.create(
            reservation=reservation,
            ticket_reference=reference,
            seat_number=1,
            qr_token=Ticket.generate_qr_token(reference),
        )

    def test_returns_generated_qr_png_to_ticket_owner(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse('tickets:qr_image', args=[self.ticket.ticket_reference])
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['Content-Type'], 'image/png')
        image = Image.open(BytesIO(response.content))
        self.assertEqual(image.format, 'PNG')

    def test_qr_image_is_not_available_to_another_participant(self):
        other_user = get_user_model().objects.create_user(
            email='other@example.com',
            password='SecurePass123',
            first_name='Other',
            last_name='Participant',
            postnom='Test',
            whatsapp_number='+243811112233',
        )
        self.client.force_login(other_user)

        response = self.client.get(
            reverse('tickets:qr_image', args=[self.ticket.ticket_reference])
        )

        self.assertEqual(response.status_code, 404)

    def test_reservation_ticket_list_uses_the_authenticated_qr_endpoint(self):
        self.client.force_login(self.user)

        response = self.client.get(
            reverse(
                'tickets:reservation_tickets',
                args=[self.ticket.reservation.reference],
            )
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            reverse('tickets:qr_image', args=[self.ticket.ticket_reference]),
        )
