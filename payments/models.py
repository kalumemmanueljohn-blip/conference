import secrets

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Payment(models.Model):
    """
    Paiement associé à une réservation.
    Méthode : SASPAY (auto) ou WhatsApp (manuel avec validation admin).
    """

    METHOD_CHOICES = [
        ('saspay', 'SASPAY'),
        ('whatsapp', 'WhatsApp'),
    ]
    STATUS_CHOICES = [
        ('pending', _('En attente')),
        ('confirmed', _('Confirmé')),
        ('rejected', _('Rejeté')),
        ('expired', _('Expiré')),
    ]

    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.PROTECT,
        related_name='payments',
        verbose_name=_("Réservation"),
    )
    method = models.CharField(
        _("Méthode"),
        max_length=20,
        choices=METHOD_CHOICES,
    )
    status = models.CharField(
        _("Statut"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    amount = models.DecimalField(
        _("Montant"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
    )
    currency = models.CharField(
        _("Devise"),
        max_length=3,
        default='USD',
        editable=False,
    )
    internal_reference = models.CharField(
        _("Référence interne"),
        max_length=32,
        unique=True,
        db_index=True,
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Mis à jour le"), auto_now=True)
    confirmed_at = models.DateTimeField(_("Confirmé le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Paiement")
        verbose_name_plural = _("Paiements")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['reservation', 'status']),
            models.Index(fields=['method', 'status']),
        ]

    def __str__(self):
        return f"{self.internal_reference} — {self.get_method_display()} ({self.get_status_display()})"

    @staticmethod
    def generate_internal_reference() -> str:
        """Génère une référence interne unique."""
        return f"PAY-{secrets.token_hex(6).upper()}"

    def mark_as_confirmed(self):
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    def mark_as_rejected(self):
        self.status = 'rejected'
        self.save(update_fields=['status', 'updated_at'])


class SaspayTransaction(models.Model):
    """
    Trace une transaction SASPAY.
    Conserve les requêtes/réponses brutes pour audit.
    """

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='saspay',
        verbose_name=_("Paiement"),
    )
    saspay_transaction_id = models.CharField(
        _("ID transaction SASPAY"),
        max_length=100,
        unique=True,
        null=True,
        blank=True,
    )
    saspay_reference = models.CharField(
        _("Référence SASPAY"),
        max_length=100,
        null=True,
        blank=True,
    )
    raw_request = models.JSONField(
        _("Requête brute"),
        default=dict,
        blank=True,
    )
    raw_response = models.JSONField(
        _("Réponse brute"),
        default=dict,
        blank=True,
    )
    signature_verified = models.BooleanField(
        _("Signature vérifiée"),
        default=False,
    )
    verified_at = models.DateTimeField(
        _("Vérifié le"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Transaction SASPAY")
        verbose_name_plural = _("Transactions SASPAY")

    def __str__(self):
        return f"SASPAY {self.saspay_transaction_id or 'en attente'}"


class WhatsappProof(models.Model):
    """
    Preuve de paiement envoyée par le participant via WhatsApp.
    Validation manuelle obligatoire par un admin.
    """

    STATUS_CHOICES = [
        ('pending', _('En attente de validation')),
        ('validated', _('Validée')),
        ('rejected', _('Rejetée')),
        ('new_proof_requested', _('Nouvelle preuve demandée')),
    ]

    payment = models.OneToOneField(
        Payment,
        on_delete=models.CASCADE,
        related_name='whatsapp_proof',
        verbose_name=_("Paiement"),
    )
    proof_file = models.FileField(
        _("Fichier de preuve"),
        upload_to='proofs/%Y/%m/',
        help_text=_("Capture d'écran ou PDF du paiement."),
    )
    uploaded_at = models.DateTimeField(_("Envoyé le"), auto_now_add=True)
    status = models.CharField(
        _("Statut"),
        max_length=30,
        choices=STATUS_CHOICES,
        default='pending',
        db_index=True,
    )
    validated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='validated_proofs',
        verbose_name=_("Validé par"),
    )
    validated_at = models.DateTimeField(_("Validé le"), null=True, blank=True)
    rejection_reason = models.TextField(_("Motif de rejet"), blank=True)

    class Meta:
        verbose_name = _("Preuve WhatsApp")
        verbose_name_plural = _("Preuves WhatsApp")

    def __str__(self):
        return f"Preuve {self.payment.internal_reference} — {self.get_status_display()}"