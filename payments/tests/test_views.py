from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import override

from conference.models import Conference
from payments.services import PaymentError, initiate_whatsapp_payment
from reservations.services import create_reservation

User = get_user_model()


@pytest.fixture(autouse=True)
def use_unmanifested_static_storage(settings):
    settings.STORAGES['staticfiles'] = {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    }
    settings.WHATSAPP_ADMIN_NUMBER = '+243830360200'


@pytest.fixture
def reservation(db):
    user = User.objects.create_user(
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
        location='Lieu test',
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )
    return create_reservation(user, conference, seats=2)


@pytest.mark.django_db
def test_payment_choice_only_offers_whatsapp(client, reservation):
    client.force_login(reservation.user)

    response = client.get(reverse(
        'payments:choose',
        kwargs={'reference': reservation.reference},
    ))

    assert response.status_code == 200
    assert 'WhatsApp' in response.content.decode()
    assert 'SASPAY' not in response.content.decode()
    assert 'Continuer avec WhatsApp' in response.content.decode()


@pytest.mark.django_db
def test_payment_choice_is_fully_translated_in_english(client, reservation):
    client.force_login(reservation.user)

    response = client.get(f'/en/payments/{reservation.reference}/')

    content = response.content.decode()
    assert response.status_code == 200
    assert '<html lang="en"' in content
    assert 'Pay with WhatsApp' in content
    assert 'Seats' in content
    assert 'Continue with WhatsApp' in content
    assert 'Contact us on WhatsApp for payment instructions' in content
    assert 'My reservations' in content
    assert 'Useful links' in content
    assert 'Ask for payment methods on WhatsApp' in content
    assert 'Hello%2C%20I%20would%20like%20to%20know' in content


@pytest.mark.django_db
def test_whatsapp_payment_instructions_are_translated_in_english(client, reservation):
    client.force_login(reservation.user)

    response = client.get(f'/en/payments/{reservation.reference}/whatsapp/')

    content = response.content.decode()
    assert response.status_code == 200
    assert '<html lang="en"' in content
    assert 'Pay via WhatsApp' in content
    assert 'Complete the payment and send a screenshot' in content
    assert 'Wait for verification' in content
    assert 'Hello, I would like to pay for my reservation.' in response.context['whatsapp_message']


@pytest.mark.django_db
def test_whatsapp_payment_errors_are_translated_in_english(reservation):
    reservation.status = 'cancelled'
    reservation.save(update_fields=['status', 'updated_at'])

    with override('en'), pytest.raises(PaymentError) as error:
        initiate_whatsapp_payment(reservation)

    assert str(error.value) == (
        f'Payment cannot be started for a reservation with status “Cancelled”.'
    )


@pytest.mark.django_db
def test_switching_from_english_to_french_redirects_to_french_home(client):
    english_home = client.get('/en/')

    assert english_home.status_code == 200
    assert 'name="next" type="hidden" value="/"' in english_home.content.decode()

    switch_response = client.post(
        '/i18n/setlang/',
        {'language': 'fr', 'next': '/'},
    )
    french_home = client.get(switch_response.url)

    assert switch_response.status_code == 302
    assert switch_response.url == '/'
    assert '<html lang="fr"' in french_home.content.decode()
