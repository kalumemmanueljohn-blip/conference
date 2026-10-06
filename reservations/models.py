import secrets

from decimal import Decimal

from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator, RegexValidator
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from conference.models import Conference


class Reservation(models.Model):
    """
    Réservation d'une ou plusieurs places à une conférence.
    Référence unique au format BGA-2026-XXXXXXX.
    """

    STATUS_CHOICES = [
        ('created', _('Créée')),
        ('payment_pending', _('Paiement en attente')),
        ('payment_confirmed', _('Paiement confirmé')),
        ('confirmed', _('Confirmée')),
        ('ticket_generated', _('Billet généré')),
        ('present', _('Présent')),
        ('cancelled', _('Annulée')),
    ]

    ACTIVE_STATUSES = [
        'created', 'payment_pending', 'payment_confirmed',
        'confirmed', 'ticket_generated', 'present',
    ]

    # ===== Identification =====
    reference = models.CharField(
        _("Référence"),
        max_length=20,
        unique=True,
        db_index=True,
        help_text=_("Format : BGA-2026-XXXXXXX (généré automatiquement si vide)."),
    )

    # ===== Relations =====
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name=_("Utilisateur"),
    )
    conference = models.ForeignKey(
        Conference,
        on_delete=models.PROTECT,
        related_name='reservations',
        verbose_name=_("Conférence"),
    )

    # ===== Détails =====
    seats = models.PositiveIntegerField(
        _("Nombre de places"),
        default=1,
        validators=[
            MinValueValidator(1),
            MaxValueValidator(5),
        ],
        help_text=_("Entre 1 et 5 places par réservation."),
    )

    payment_phone_number = models.CharField(
        _("Numéro à débiter"),
        max_length=20,
        blank=True,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9]{9,15}$',
                message=_("Format international requis (ex: +243812345678)."),
            )
        ],
        help_text=_(
            "Numéro mobile money qui recevra la demande de paiement. "
            "Par défaut : votre numéro WhatsApp."
        ),
    )

    status = models.CharField(
        _("Statut"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='created',
        db_index=True,
    )
    payment_method = models.CharField(
        _("Méthode de paiement"),
        max_length=20,
        choices=[
            ('saspay', 'SASPAY'),
            ('whatsapp', 'WhatsApp'),
        ],
        null=True,
        blank=True,
    )
    saspay_network = models.CharField(
        _("Réseau SASPAY"),
        max_length=30,
        blank=True,
        choices=[
            ('vodacom_cd_usd', 'Vodacom Congo (USD)'),
            ('airtel_cd_usd', 'Airtel Congo (USD)'),
            ('orange_cd_usd', 'Orange Congo (USD)'),
        ],
        help_text=_("Réseau mobile money pour le paiement SASPAY (USD)."),
    )
    total_amount = models.DecimalField(
        _("Montant total"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('0.00'),
        help_text=_("Montant figé au moment de la création."),
    )
    currency = models.CharField(
        _("Devise"),
        max_length=3,
        default='USD',
        editable=False,
    )

    # ===== Dates =====
    created_at = models.DateTimeField(_("Créée le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Mise à jour le"), auto_now=True)
    confirmed_at = models.DateTimeField(_("Confirmée le"), null=True, blank=True)
    cancelled_at = models.DateTimeField(_("Annulée le"), null=True, blank=True)

    class Meta:
        verbose_name = _("Réservation")
        verbose_name_plural = _("Réservations")
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['user', 'conference', 'status']),
            models.Index(fields=['reference']),
            models.Index(fields=['status']),
        ]
        # ⚠️ Contrainte d'unicité retirée : un user peut avoir plusieurs réservations
    
    def __str__(self):
        return f"{self.reference} — {self.user.full_name} ({self.get_status_display()})"

    def get_absolute_url(self):
        return reverse('reservations:detail', kwargs={'reference': self.reference})

    def save(self, *args, **kwargs):
        if not self.reference:
            self.reference = self.generate_reference()
        # Si le numéro de paiement est vide, utiliser le WhatsApp du user
        if not self.payment_phone_number and self.user_id:
            self.payment_phone_number = self.user.whatsapp_number
        super().save(*args, **kwargs)

    # ===== Méthodes métier =====

    @staticmethod
    def generate_reference() -> str:
        """Génère une référence unique au format BGA-2026-XXXXXXX."""
        year = timezone.now().year
        random_part = secrets.token_hex(4).upper()
        return f"BGA-{year}-{random_part}"

    def compute_total_amount(self) -> Decimal:
        """Calcule le montant total = prix × places."""
        if self.conference.is_free:
            return Decimal('0.00')
        return self.conference.price_per_seat * self.seats

    def mark_as_payment_pending(self, method: str = None):
        """Passe la réservation en attente de paiement."""
        self.status = 'payment_pending'
        if method:
            self.payment_method = method
        self.save(update_fields=['status', 'payment_method', 'updated_at'])

    def mark_as_confirmed(self):
        """Confirme la réservation (paiement validé)."""
        self.status = 'confirmed'
        self.confirmed_at = timezone.now()
        self.save(update_fields=['status', 'confirmed_at', 'updated_at'])

    def mark_as_cancelled(self):
        """Annule la réservation."""
        self.status = 'cancelled'
        self.cancelled_at = timezone.now()
        self.save(update_fields=['status', 'cancelled_at', 'updated_at'])

    # ===== Propriétés =====

    @property
    def is_active(self) -> bool:
        return self.status in self.ACTIVE_STATUSES

    @property
    def is_confirmed(self) -> bool:
        return self.status in ['confirmed', 'ticket_generated', 'present']

    @property
    def can_be_cancelled(self) -> bool:
        return self.status in ['created', 'payment_pending']

    def total_amount_display(self) -> str:
        if self.conference.is_free or self.total_amount == 0:
            return _("Gratuit")
        return f"{self.total_amount} {self.currency}"