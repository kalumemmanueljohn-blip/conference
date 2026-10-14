from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone

from conference.models import Conference
from reservations.services import confirm_reservation, create_reservation
from tickets.services import generate_ticket

User = get_user_model()


@pytest.fixture(autouse=True)
def use_unmanifested_static_storage(settings):
    settings.STORAGES['staticfiles'] = {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    }


@pytest.fixture
def checkin_data(db):
    admin = User.objects.create_superuser(
        email='admin@example.com',
        password='AdminPass123',
        first_name='Admin',
        last_name='Root',
        postnom='Sys',
        whatsapp_number='+243830360200',
    )
    attendee = User.objects.create_user(
        email='jean@example.com',
        password='SecurePass123',
        first_name='Jean',
        last_name='Kabila',
        postnom='Mwamba',
        whatsapp_number='+243812345678',
    )
    conference = Conference.objects.create(
        title='Conférence test active',
        date=timezone.now() + timedelta(days=30),
        location='Lieu',
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )
    reservation = create_reservation(attendee, conference, seats=2)
    confirm_reservation(reservation)
    ticket = generate_ticket(reservation)[0]
    return admin, attendee, ticket


@pytest.mark.django_db
def test_checkin_page_lists_and_searches_attendees(client, checkin_data):
    admin, attendee, ticket = checkin_data
    client.force_login(admin)

    response = client.get(reverse('dashboard:checkin'))
    assert response.status_code == 200
    assert response.context['attendance']['total'] == 2
    assert response.context['page_obj'].paginator.count == 2

    response = client.get(reverse('dashboard:checkin'), {'q': attendee.email})
    assert response.status_code == 200
    assert response.context['page_obj'].paginator.count == 2
    assert attendee.first_name in response.content.decode()
    assert ticket.ticket_reference in response.content.decode()


@pytest.mark.django_db
def test_checkin_confirms_ticket_and_reports_already_used(client, checkin_data):
    admin, _, ticket = checkin_data
    client.force_login(admin)
    checkin_url = reverse(
        'dashboard:checkin_confirm',
        args=[ticket.ticket_reference],
    )

    response = client.post(checkin_url)
    assert response.status_code == 302
    assert response['Location'] == (
        f"{reverse('dashboard:checkin')}?q={ticket.ticket_reference}"
    )

    ticket.refresh_from_db()
    assert ticket.status == 'used'
    assert ticket.checked_by == admin
    assert ticket.used_at is not None

    response = client.get(
        reverse('dashboard:checkin'),
        {'q': ticket.qr_token},
    )
    assert response.status_code == 200
    assert response.context['ticket'] == ticket
    assert response.context['attendance']['used'] == 1
    assert 'Billet déjà utilisé' in response.content.decode()
    assert 'Contrôlé par' in response.content.decode()


@pytest.mark.django_db
def test_checkin_requires_staff(client):
    user = User.objects.create_user(
        email='participant@example.com',
        password='SecurePass123',
    )
    client.force_login(user)

    response = client.get(reverse('dashboard:checkin'))

    assert response.status_code == 302


@pytest.mark.django_db
def test_checkin_cannot_validate_ticket_from_another_conference(client, checkin_data):
    admin, _, ticket = checkin_data
    Conference.objects.filter(
        pk=ticket.reservation.conference_id,
    ).update(is_active=False)
    Conference.objects.create(
        title='Conférence suivante',
        date=timezone.now() + timedelta(days=60),
        location='Autre lieu',
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )
    client.force_login(admin)

    response = client.post(reverse(
        'dashboard:checkin_confirm',
        args=[ticket.ticket_reference],
    ))

    assert response.status_code == 302
    ticket.refresh_from_db()
    assert ticket.status == 'generated'
