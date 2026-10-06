import hashlib
import hmac

from django.conf import settings
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _


class Ticket(models.Model):
    """
    Billet électronique associé à UNE place d'une réservation.
    Une réservation de N places génère N billets indépendants.

    Format de référence : BGA-2026-XXXXXXX-01 (jusqu'à -05)
    """

    STATUS_CHOICES = [
        ('generated', _('Généré')),
        ('used', _('Utilisé')),
        ('cancelled', _('Annulé')),
    ]

    reservation = models.ForeignKey(
        'reservations.Reservation',
        on_delete=models.PROTECT,
        related_name='tickets',
        verbose_name=_("Réservation"),
    )
    ticket_reference = models.CharField(
        _("Référence billet"),
        max_length=25,
        unique=True,
        db_index=True,
        help_text=_("Format : BGA-2026-XXXXXXX-01"),
    )
    seat_number = models.PositiveIntegerField(
        _("Numéro de place"),
        default=1,
        help_text=_("Position dans la réservation (1 à N)."),
    )
    qr_token = models.CharField(
        _("Token QR"),
        max_length=64,
        unique=True,
        db_index=True,
        help_text=_("Token HMAC signé, sans données personnelles."),
    )
    qr_image = models.ImageField(
        _("Image QR"),
        upload_to='tickets/qr/%Y/%m/',
        null=True,
        blank=True,
    )
    pdf_file = models.FileField(
        _("Fichier PDF individuel"),
        upload_to='tickets/pdf/%Y/%m/',
        null=True,
        blank=True,
    )
    status = models.CharField(
        _("Statut"),
        max_length=20,
        choices=STATUS_CHOICES,
        default='generated',
        db_index=True,
    )
    generated_at = models.DateTimeField(_("Généré le"), auto_now_add=True)
    used_at = models.DateTimeField(_("Utilisé le"), null=True, blank=True)
    checked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='checked_tickets',
        verbose_name=_("Contrôlé par"),
    )

    class Meta:
        verbose_name = _("Billet")
        verbose_name_plural = _("Billets")
        ordering = ['reservation', 'seat_number']
        indexes = [
            models.Index(fields=['ticket_reference']),
            models.Index(fields=['qr_token']),
            models.Index(fields=['status']),
        ]
        constraints = [
            # Une place unique par réservation
            models.UniqueConstraint(
                fields=['reservation', 'seat_number'],
                name='unique_seat_per_reservation',
            ),
        ]

    def __str__(self):
        return (
            f"{self.ticket_reference} — "
            f"{self.reservation.user.full_name} "
            f"(Place {self.seat_number}/{self.reservation.seats}, "
            f"{self.get_status_display()})"
        )

    def get_absolute_url(self):
        return reverse('tickets:detail', kwargs={'reference': self.ticket_reference})

    # ===== QR =====

    @staticmethod
    def generate_qr_token(ticket_reference: str) -> str:
        """Génère un token HMAC-SHA256 signé."""
        signature = hmac.new(
            settings.SECRET_KEY.encode(),
            ticket_reference.encode(),
            hashlib.sha256,
        ).hexdigest()[:16]
        return f"{ticket_reference}.{signature}"

    @staticmethod
    def verify_qr_token(token: str):
        """Vérifie un token QR. Retourne la référence ou None."""
        try:
            reference, signature = token.rsplit('.', 1)
        except ValueError:
            return None

        expected = Ticket.generate_qr_token(reference).rsplit('.', 1)[1]
        if not hmac.compare_digest(signature, expected):
            return None
        return reference

    # ===== Propriétés =====

    @property
    def is_usable(self) -> bool:
        return self.status == 'generated'

    @property
    def is_used(self) -> bool:
        return self.status == 'used'

    @property
    def seat_label(self) -> str:
        """Ex: Place 2/4"""
        return f"Place {self.seat_number}/{self.reservation.seats}"

    def mark_as_used(self, admin_user):
        """Marque le billet comme utilisé."""
        self.status = 'used'
        self.used_at = timezone.now()
        self.checked_by = admin_user
        self.save(update_fields=['status', 'used_at', 'checked_by'])