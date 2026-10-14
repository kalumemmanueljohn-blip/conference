import pytest
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@pytest.fixture(autouse=True)
def use_unmanifested_static_storage(settings):
    settings.STORAGES['staticfiles'] = {
        'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage',
    }


@pytest.mark.django_db
class TestRegistrationView:

    def test_register_page_loads(self, client):
        response = client.get(reverse('accounts:register'))
        assert response.status_code == 200

    def test_register_creates_user_and_logs_in(self, client):
        response = client.post(reverse('accounts:register'), {
            'username': 'jean-kabila',
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
            'username': 'jean-kabila-2',
            'last_name': 'K', 'postnom': 'M', 'first_name': 'J',
            'email': 'jean@example.com', 'whatsapp_number': '+243812345679',
            'password1': 'SecurePass123', 'password2': 'SecurePass123',
        })
        assert response.status_code == 200
        assert User.objects.filter(email='jean@example.com').count() == 1

    def test_register_without_email(self, client):
        response = client.post(reverse('accounts:register'), {
            'username': 'jean-sans-email',
            'last_name': 'Kabila',
            'postnom': 'Mwamba',
            'first_name': 'Jean',
            'email': '',
            'whatsapp_number': '+243812345678',
            'password1': 'SecurePass123',
            'password2': 'SecurePass123',
        })
        user = User.objects.get(username='jean-sans-email')
        assert response.status_code == 302
        assert user.email is None
        assert int(client.session['_auth_user_id']) == user.pk


@pytest.mark.django_db
class TestLoginView:

    def test_login_with_username(self, client):
        User.objects.create_user(
            username='jean-kabila', email='jean@example.com',
            password='SecurePass123',
            first_name='J', last_name='K', postnom='M', whatsapp_number='+243812345678',
        )
        response = client.post(reverse('accounts:login'), {
            'username': 'jean-kabila',
            'password': 'SecurePass123',
        })
        assert response.status_code == 302

    def test_existing_email_as_legacy_username_still_works(self, client):
        User.objects.create_user(
            email='jean@example.com',
            password='SecurePass123',
            first_name='J',
            last_name='K',
            postnom='M',
            whatsapp_number='+243812345678',
        )
        response = client.post(reverse('accounts:login'), {
            'username': 'jean@example.com',
            'password': 'SecurePass123',
        })
        assert response.status_code == 302