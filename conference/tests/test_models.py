from datetime import timedelta
from decimal import Decimal

import pytest
from django.utils import timezone

from conference.models import Conference


@pytest.fixture
def conference_data():
    """Données de base pour créer une conférence."""
    return {
        'title': "L'entrepreneuriat des jeunes à Kinshasa",
        'date': timezone.now() + timedelta(days=30),
        'location': "Auditorium du CHESD GOMBE",
        'price_per_seat': Decimal('5.70'),
        'total_seats': 100,
    }


@pytest.mark.django_db
class TestConferenceModel:

    def test_create_conference(self, conference_data):
        conference = Conference.objects.create(**conference_data)
        assert conference.title == conference_data['title']
        assert conference.is_active is False
        assert conference.slug != ''
        assert conference.currency == 'USD'

    def test_slug_auto_generated(self, conference_data):
        conference = Conference.objects.create(**conference_data)
        assert 'entrepreneuriat' in conference.slug
        assert ' ' not in conference.slug
        assert conference.slug.islower()

    def test_slug_unique(self, conference_data):
        Conference.objects.create(**conference_data)
        with pytest.raises(Exception):
            Conference.objects.create(**conference_data)

    def test_only_one_active_conference(self, conference_data):
        c1 = Conference.objects.create(**conference_data, is_active=True)
        c2 = Conference.objects.create(
            title="Autre conférence",
            date=timezone.now() + timedelta(days=60),
            location="Autre lieu",
            is_active=True,
        )
        c1.refresh_from_db()
        assert c1.is_active is False
        assert c2.is_active is True
        assert Conference.objects.filter(is_active=True).count() == 1

    def test_get_active_manager(self, conference_data):
        assert Conference.objects.get_active() is None
        c = Conference.objects.create(**conference_data, is_active=True)
        assert Conference.objects.get_active() == c

    def test_price_display(self, conference_data):
        conference = Conference.objects.create(**conference_data)
        assert conference.price_display() == "5.70 USD"

    def test_price_display_free(self, conference_data):
        conference = Conference.objects.create(**conference_data, is_free=True)
        assert conference.price_display() == "Gratuit"

    def test_is_upcoming(self, conference_data):
        conference = Conference.objects.create(**conference_data)
        assert conference.is_upcoming is True
        assert conference.is_past is False

    def test_is_past(self):
        conference = Conference.objects.create(
            title="Ancienne conférence",
            date=timezone.now() - timedelta(days=30),
            location="Lieu",
        )
        assert conference.is_past is True
        assert conference.is_upcoming is False

    def test_seats_remaining_unlimited(self, conference_data):
        """total_seats = 0 → capacité illimitée → seats_remaining retourne 0."""
        conference_data['total_seats'] = 0
        conference = Conference.objects.create(**conference_data)
        assert conference.total_seats == 0
        assert conference.seats_remaining == 0
        assert conference.is_full is False

    def test_seats_remaining_calculated(self, conference_data):
        """total_seats = 100 → seats_remaining retourne 100 (aucune réservation)."""
        conference = Conference.objects.create(**conference_data)
        assert conference.seats_taken == 0
        assert conference.seats_remaining == 100
        assert conference.is_full is False

    def test_get_absolute_url(self, conference_data):
        conference = Conference.objects.create(**conference_data)
        url = conference.get_absolute_url()
        assert '/conference/' in url
        assert conference.slug in url