from datetime import timedelta
from decimal import Decimal

import pytest
from django.contrib.auth import get_user_model
from django.utils import timezone

from conference.models import Conference
from payments.models import Payment, SaspayTransaction, WhatsappProof
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


@pytest.mark.django_db
class TestPaymentModel:

    def test_generate_internal_reference(self):
        ref = Payment.generate_internal_reference()
        assert ref.startswith('PAY-')
        assert len(ref) == 16   # PAY- + 12 hex

    def test_create_payment(self, reservation):
        payment = Payment.objects.create(
            reservation=reservation,
            method='whatsapp',
            amount=reservation.total_amount,
            internal_reference=Payment.generate_internal_reference(),
        )
        assert payment.status == 'pending'
        assert payment.currency == 'USD'

    def test_mark_as_confirmed(self, reservation):
        payment = Payment.objects.create(
            reservation=reservation,
            method='whatsapp',
            amount=Decimal('11.40'),
            internal_reference=Payment.generate_internal_reference(),
        )
        payment.mark_as_confirmed()
        assert payment.status == 'confirmed'
        assert payment.confirmed_at is not None


@pytest.mark.django_db
class TestSaspayTransaction:

    def test_create_transaction(self, reservation):
        payment = Payment.objects.create(
            reservation=reservation,
            method='saspay',
            amount=reservation.total_amount,
            internal_reference=Payment.generate_internal_reference(),
        )
        tx = SaspayTransaction.objects.create(payment=payment)
        assert tx.signature_verified is False


@pytest.mark.django_db
class TestWhatsappProof:

    def test_create_proof(self, reservation):
        payment = Payment.objects.create(
            reservation=reservation,
            method='whatsapp',
            amount=reservation.total_amount,
            internal_reference=Payment.generate_internal_reference(),
        )
        proof = WhatsappProof.objects.create(
            payment=payment,
            proof_file='proofs/test.jpg',
        )
        assert proof.status == 'pending'