import pytest
from django.contrib.auth import get_user_model

User = get_user_model()


@pytest.mark.django_db
class TestUserModel:

    def test_create_user_with_email(self):
        user = User.objects.create_user(
            username='test-user',
            email='test@example.com',
            password='SecurePass123',
            first_name='Jean',
            last_name='Kabila',
            postnom='Mwamba',
            whatsapp_number='+243812345678',
        )
        assert user.email == 'test@example.com'
        assert user.check_password('SecurePass123')
        assert user.is_participant is True
        assert user.is_staff is False

    def test_create_user_without_email(self):
        first_user = User.objects.create_user(
            username='no-email-user',
            password='SecurePass123',
            first_name='Jean',
            last_name='Kabila',
            postnom='Mwamba',
            whatsapp_number='+243812345678',
        )
        second_user = User.objects.create_user(
            username='another-no-email-user',
            password='SecurePass123',
            first_name='Marie',
            last_name='Kabila',
            postnom='Mwamba',
            whatsapp_number='+243812345679',
        )
        assert first_user.email is None
        assert first_user.username == 'no-email-user'
        assert first_user.check_password('SecurePass123')
        assert second_user.email is None

    def test_create_superuser_without_email(self):
        admin = User.objects.create_superuser(
            username='site-admin',
            password='AdminPass123',
            first_name='Admin',
            last_name='Root',
            postnom='Sys',
            whatsapp_number='+243830360200',
        )
        assert admin.email is None
        assert admin.is_staff is True
        assert admin.is_superuser is True

    def test_email_is_unique(self):
        User.objects.create_user(
            email='test@example.com', password='pass12345',
            first_name='A', last_name='B', postnom='C', whatsapp_number='+243812345678',
        )
        with pytest.raises(Exception):
            User.objects.create_user(
                email='test@example.com', password='pass12345',
                first_name='X', last_name='Y', postnom='Z', whatsapp_number='+243812345679',
            )

    def test_profile_auto_created(self):
        user = User.objects.create_user(
            email='test@example.com', password='pass12345',
            first_name='A', last_name='B', postnom='C', whatsapp_number='+243812345678',
        )
        assert hasattr(user, 'profile')
        assert user.profile is not None

    def test_full_name_property(self):
        user = User.objects.create_user(
            email='test@example.com', password='pass12345',
            first_name='Jean', last_name='Kabila', postnom='Mwamba',
            whatsapp_number='+243812345678',
        )
        assert user.full_name == 'KABILA Mwamba Jean'

    def test_create_superuser(self):
        admin = User.objects.create_superuser(
            email='admin@example.com', password='AdminPass123',
            first_name='Admin', last_name='Root', postnom='Sys',
            whatsapp_number='+243812345678',
        )
        assert admin.is_staff is True
        assert admin.is_superuser is True
        assert admin.is_participant is False