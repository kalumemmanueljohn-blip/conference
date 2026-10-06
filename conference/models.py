from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q, Sum
from django.urls import reverse
from django.utils import timezone
from django.utils.text import slugify
from django.utils.translation import gettext_lazy as _

from .managers import ConferenceManager


class Conference(models.Model):
    """
    Représente une conférence organisée par Bantondo's Génération ASBL.

    Règle métier : une seule conférence peut être active à la fois.
    """

    # ===== Informations principales =====
    title = models.CharField(
        _("Titre"),
        max_length=255,
        help_text=_("Ex: L'entrepreneuriat des jeunes à Kinshasa, Mythe ou Réalité ?"),
    )
    slug = models.SlugField(
        _("Slug URL"),
        max_length=280,
        unique=True,
        blank=True,
        help_text=_("Généré automatiquement depuis le titre si laissé vide."),
    )
    organization_name = models.CharField(
        _("Nom de l'organisation"),
        max_length=200,
        default="Bantondo's Génération ASBL",
    )

    # ===== Date, lieu =====
    date = models.DateTimeField(
        _("Date et heure"),
        help_text=_("Ex: 27 novembre 2026 à 14h00"),
    )
    location = models.CharField(
        _("Lieu"),
        max_length=255,
        help_text=_("Ex: Auditorium du CHESD GOMBE"),
    )

    # ===== Contenu éditorial =====
    description = models.TextField(
        _("Description"),
        blank=True,
        default="À compléter",
    )
    objective = models.TextField(
        _("Objectif"),
        blank=True,
        default="À compléter",
    )
    practical_info = models.TextField(
        _("Informations pratiques"),
        blank=True,
        default="À compléter",
    )

    # ===== Médias =====
    poster = models.ImageField(
        _("Affiche de la conférence"),
        upload_to='conference/posters/',
        null=True,
        blank=True,
        help_text=_("Affiche officielle (JPG, PNG). Format portrait recommandé."),
    )

        # ===== Contacts =====
    contact_phone = models.CharField(
        _("Téléphone"),
        max_length=30,
        blank=True,
        help_text=_("Ex: +243986698720"),
    )
    contact_email = models.EmailField(
        _("Email de contact"),
        blank=True,
        help_text=_("Ex: contact@bantondos.cd"),
    )
    contact_address = models.CharField(
        _("Adresse physique"),
        max_length=255,
        blank=True,
        help_text=_("Ex: Avenue X, Gombe, Kinshasa"),
    )

    # ===== Réseaux sociaux =====
    social_facebook = models.URLField(
        _("Facebook"),
        blank=True,
        help_text=_("URL complète : https://facebook.com/..."),
    )
    social_instagram = models.URLField(
        _("Instagram"),
        blank=True,
        help_text=_("URL complète : https://instagram.com/..."),
    )
    social_twitter = models.URLField(
        _("X (Twitter)"),
        blank=True,
        help_text=_("URL complète : https://x.com/..."),
    )
    social_tiktok = models.URLField(
        _("TikTok"),
        blank=True,
        help_text=_("URL complète : https://tiktok.com/@..."),
    )
    social_linkedin = models.URLField(
        _("LinkedIn"),
        blank=True,
        help_text=_("URL complète : https://linkedin.com/..."),
    )
    social_youtube = models.URLField(
        _("YouTube"),
        blank=True,
        help_text=_("URL complète : https://youtube.com/..."),
    )

    # ===== Tarification =====
    is_free = models.BooleanField(
        _("Gratuit"),
        default=False,
        help_text=_("Décocher pour une conférence payante."),
    )
    price_per_seat = models.DecimalField(
        _("Prix par place"),
        max_digits=10,
        decimal_places=2,
        default=Decimal('5.70'),
        validators=[MinValueValidator(Decimal('0.00'))],
        help_text=_("Montant en USD par place."),
    )
    currency = models.CharField(
        _("Devise"),
        max_length=3,
        default='USD',
        editable=False,
    )

    # ===== Capacité =====
    total_seats = models.PositiveIntegerField(
        _("Nombre total de places"),
        default=0,
        help_text=_("Laisser à 0 si la capacité est illimitée."),
    )

    # ===== Statut =====
    is_active = models.BooleanField(
        _("Active"),
        default=False,
        help_text=_(
            "Une seule conférence peut être active à la fois. "
            "Activer celle-ci désactivera automatiquement les autres."
        ),
    )

    # ===== Métadonnées =====
    created_at = models.DateTimeField(_("Créée le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Mise à jour le"), auto_now=True)

    objects = ConferenceManager()

    class Meta:
        verbose_name = _("Conférence")
        verbose_name_plural = _("Conférences")
        ordering = ['-date']
        constraints = [
            models.UniqueConstraint(
                fields=['is_active'],
                condition=Q(is_active=True),
                name='unique_active_conference',
            ),
        ]

    def __str__(self):
        status = "ACTIVE" if self.is_active else "archivée"
        return f"{self.title} ({status})"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.title)[:280]
        if self.is_active:
            Conference.objects.exclude(pk=self.pk).filter(is_active=True).update(is_active=False)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('conference:detail', kwargs={'slug': self.slug})

    # ===== Propriétés calculées =====

    @property
    def seats_taken(self):
        try:
            from reservations.models import Reservation
        except ImportError:
            return 0
        result = Reservation.objects.filter(
            conference=self,
            status__in=[
                'created', 'payment_pending', 'payment_confirmed',
                'confirmed', 'ticket_generated', 'present',
            ],
        ).aggregate(total=Sum('seats'))
        return result['total'] or 0

    @property
    def seats_remaining(self):
        if self.total_seats == 0:
            return 0
        return max(self.total_seats - self.seats_taken, 0)

    @property
    def is_full(self):
        if self.total_seats == 0:
            return False
        return self.seats_taken >= self.total_seats

    @property
    def is_upcoming(self):
        return self.date > timezone.now()

    @property
    def is_past(self):
        return self.date <= timezone.now()

    def price_display(self):
        if self.is_free:
            return "Gratuit"
        return f"{self.price_per_seat} {self.currency}"


class Speaker(models.Model):
    """
    Intervenant d'une conférence.
    Géré via l'admin Django avec upload de photo.
    """

    conference = models.ForeignKey(
        Conference,
        on_delete=models.CASCADE,
        related_name='speakers',
        verbose_name=_("Conférence"),
    )
    name = models.CharField(
        _("Nom complet"),
        max_length=150,
        help_text=_("Ex: Jean KABILA"),
    )
    role = models.CharField(
        _("Fonction / Titre"),
        max_length=200,
        help_text=_("Ex: Entrepreneur social, Fondateur de XYZ"),
    )
    bio = models.TextField(
        _("Biographie"),
        blank=True,
        help_text=_("Courte biographie (optionnelle)."),
    )
    photo = models.ImageField(
        _("Photo"),
        upload_to='conference/speakers/%Y/%m/',
        null=True,
        blank=True,
        help_text=_("Format carré recommandé (min 400x400px)."),
    )
    order = models.PositiveIntegerField(
        _("Ordre d'affichage"),
        default=0,
        help_text=_("Les plus petits nombres apparaissent en premier."),
    )
    is_visible = models.BooleanField(
        _("Visible sur le site"),
        default=True,
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)

    class Meta:
        verbose_name = _("Intervenant")
        verbose_name_plural = _("Intervenants")
        ordering = ['order', 'name']

    def __str__(self):
        return f"{self.name} — {self.role}"

    @property
    def initials(self):
        """Retourne les initiales pour le placeholder."""
        parts = self.name.split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.name[:2].upper()