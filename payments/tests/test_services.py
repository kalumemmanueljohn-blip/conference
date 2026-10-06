from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from payments.models import Payment, WhatsappProof
from payments.services import (
    PaymentError,
    initiate_whatsapp_payment,
    reject_whatsapp_payment,
    submit_whatsapp_proof,
    validate_whatsapp_payment,
)
from reservations.services import create_reservation

User = get_user_model()


@pytest.fixture
def reservation(db):
    user = User.objects.create_user(
        email='jean@example.com', password='SecurePass123',
        first_name='Jean', last_name='Kabila', postnom='Mwamba',
        whatsapp_number='+243812345678',
    )
    conference = Conference.objects.create(
        title="Conférence test",
        date=timezone.now() + timedelta(days=30),
        location="Lieu test",
        price_per_seat=Decimal('5.70'),
        total_seats=100,
        is_active=True,
    )
    return create_reservation(user, conference, seats=2)


@pytest.fixture
def admin_user(db):
    return User.objects.create_superuser(
        email='admin@example.com', password='AdminPass123',
        first_name='Admin', last_name='Root', postnom='Sys',
        whatsapp_number='+243812345678',
    )


@pytest.mark.django_db
class TestWhatsappPaymentFlow:

    def test_initiate_whatsapp_payment(self, reservation):
        payment = initiate_whatsapp_payment(reservation)
        assert payment.method == 'whatsapp'
        assert payment.status == 'pending'
        assert reservation.status == 'payment_pending'

    def test_submit_proof(self, reservation):
        payment = initiate_whatsapp_payment(reservation)
        proof = submit_whatsapp_proof(payment, 'proofs/test.jpg')
        assert proof.status == 'pending'
        assert proof.payment == payment

    def test_validate_whatsapp_payment(self, reservation, admin_user):
        payment = initiate_whatsapp_payment(reservation)
        proof = submit_whatsapp_proof(payment, 'proofs/test.jpg')
        validate_whatsapp_payment(proof, admin_user)

        payment.refresh_from_db()
        reservation.refresh_from_db()
        assert payment.status == 'confirmed'
        assert reservation.status == 'confirmed'
        assert proof.status == 'validated'
        assert proof.validated_by == admin_user

    def test_reject_whatsapp_payment(self, reservation, admin_user):
        payment = initiate_whatsapp_payment(reservation)
        proof = submit_whatsapp_proof(payment, 'proofs/test.jpg')
        reject_whatsapp_payment(proof, admin_user, reason="Illisible")

        payment.refresh_from_db()
        assert payment.status == 'rejected'
        assert proof.status == 'rejected'
        assert proof.rejection_reason == "Illisible"

    def test_cannot_validate_twice(self, reservation, admin_user):
        payment = initiate_whatsapp_payment(reservation)
        proof = submit_whatsapp_proof(payment, 'proofs/test.jpg')
        validate_whatsapp_payment(proof, admin_user)
        with pytest.raises(PaymentError, match="déjà traitée"):
            validate_whatsapp_payment(proof, admin_user)