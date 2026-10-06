import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.mark.django_db
class TestRegistrationView:

    def test_register_page_loads(self, client):
        response = client.get(reverse('accounts:register'))
        assert response.status_code == 200

    def test_register_creates_user_and_logs_in(self, client):
        response = client.post(reverse('accounts:register'), {
            'last_name': 'Kabila',
            'postnom': 'Mwamba',
            'first_name': 'Jean',
            'email': 'jean@example.com',
            'whatsapp_number': '+243812345678',
            'password1': 'SecurePass123',
            'password2': 'SecurePass123',
        })
        assert response.status_code == 302
        assert User.objects.filter(email='jean@example.com').exists()

    def test_duplicate_email_rejected(self, client):
        User.objects.create_user(
            email='jean@example.com', password='pass12345',
            first_name='J', last_name='K', postnom='M', whatsapp_number='+243812345678',
        )
        response = client.post(reverse('accounts:register'), {
            'last_name': 'K', 'postnom': 'M', 'first_name': 'J',
            'email': 'jean@example.com', 'whatsapp_number': '+243812345679',
            'password1': 'SecurePass123', 'password2': 'SecurePass123',
        })
        assert response.status_code == 200
        assert User.objects.filter(email='jean@example.com').count() == 1


@pytest.mark.django_db
class TestLoginView:

    def test_login_with_email(self, client):
        User.objects.create_user(
            email='jean@example.com', password='SecurePass123',
            first_name='J', last_name='K', postnom='M', whatsapp_number='+243812345678',
        )
        response = client.post(reverse('accounts:login'), {
            'username': 'jean@example.com',
            'password': 'SecurePass123',
        })
        assert response.status_code == 302