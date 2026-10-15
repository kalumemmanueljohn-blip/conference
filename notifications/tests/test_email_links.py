from datetime import datetime, timezone as datetime_timezone
from html import unescape
from types import SimpleNamespace
from unittest.mock import patch

from django.contrib.auth.models import AnonymousUser
from django.core import mail
from django.template.loader import render_to_string
from django.test import SimpleTestCase, override_settings
from django.test.client import RequestFactory
from django.urls import reverse

from config.context_processors import footer_contact, whatsapp_contact
from notifications.services import (
    send_ticket_ready_email,
    send_welcome_email,
    send_whatsapp_rejected_email,
)


@override_settings(
    EMAIL_BACKEND='django.core.mail.backends.locmem.EmailBackend',
    SITE_URL='https://www.bantondos.site/',
)
class TransactionalEmailLinkTests(SimpleTestCase):
    def setUp(self):
        mail.outbox.clear()
        self.user = SimpleNamespace(
            email='participant@example.com',
            first_name='Participant',
        )
        self.reservation = SimpleNamespace(
            reference='BGA-2026-1234567',
            user=self.user,
            conference=SimpleNamespace(
                title='Conférence de test',
                date=datetime(2026, 11, 27, 14, 0, tzinfo=datetime_timezone.utc),
                location='Kinshasa',
            ),
        )

    def test_welcome_email_has_absolute_login_link(self):
        send_welcome_email(self.user)

        expected_url = f'https://www.bantondos.site{reverse("accounts:login")}'
        self.assertIn(f'href="{expected_url}"', mail.outbox[0].alternatives[0][0])

    def test_ticket_email_has_absolute_ticket_link(self):
        self.reservation.tickets = _TicketCollection()

        send_ticket_ready_email(self.reservation)

        expected_url = (
            'https://www.bantondos.site'
            + reverse(
                'tickets:reservation_tickets',
                args=[self.reservation.reference],
            )
        )
        self.assertIn(f'href="{expected_url}"', mail.outbox[0].alternatives[0][0])

    def test_rejected_proof_email_links_to_reservation(self):
        proof = SimpleNamespace(
            payment=SimpleNamespace(reservation=self.reservation),
            rejection_reason='Preuve illisible',
        )

        send_whatsapp_rejected_email(proof)

        expected_url = (
            'https://www.bantondos.site'
            + reverse(
                'reservations:detail',
                args=[self.reservation.reference],
            )
        )
        self.assertIn(f'href="{expected_url}"', mail.outbox[0].alternatives[0][0])

    @override_settings(
        WHATSAPP_ADMIN_NUMBER='',
        WHATSAPP_PAYMENT_NUMBER='+243830360200',
    )
    def test_footer_whatsapp_link_uses_configured_contact_number(self):
        contact = whatsapp_contact(SimpleNamespace())

        self.assertEqual(contact['whatsapp_contact_number'], '+243830360200')
        self.assertTrue(
            contact['whatsapp_contact_url'].startswith(
                'https://wa.me/243830360200?text='
            )
        )


class _TicketCollection:
    def all(self):
        return self

    def count(self):
        return 0

    def __iter__(self):
        return iter(())


class FooterContactTests(SimpleTestCase):
    @override_settings(
        WHATSAPP_ADMIN_NUMBER='+243830360200',
        WHATSAPP_PAYMENT_NUMBER='+243830360200',
    )
    def test_footer_renders_the_provided_organization_contacts_and_developer(self):
        request = RequestFactory().get('/')

        with patch('config.context_processors.get_active_conference', return_value=None):
            context = footer_contact(request)
            context.update(whatsapp_contact(request))
            context['user'] = AnonymousUser()
            html = render_to_string('partials/_footer.html', context)

        for contact in (
            'Kinshasa, RDC',
            '+243986698720',
            'bantondosgeneration@gmail.com',
            'Facebook : BG/Absl',
            'Instagram : BG/Asbl',
            "@Bantondo'sGeneration",
            "TikTok : Bantondo's Generation",
            'Développé par Kalume Emmanuel John',
            'WhatsApp : +243830360200',
        ):
            self.assertIn(contact, unescape(html))
