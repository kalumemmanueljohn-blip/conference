from django.contrib.auth.models import AbstractUser
from django.core.validators import RegexValidator
from django.db import models
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractUser):
    """
    Utilisateur custom.
    Connexion par email. Champs spécifiques RDC : postnom + WhatsApp.
    """

    email = models.EmailField(
        _("Adresse email"),
        unique=True,
        help_text=_("Utilisée comme identifiant de connexion."),
    )
    postnom = models.CharField(
        _("Postnom"),
        max_length=100,
        help_text=_("Postnom tel qu'il apparaît sur la pièce d'identité."),
    )
    whatsapp_number = models.CharField(
        _("Numéro WhatsApp"),
        max_length=20,
        validators=[
            RegexValidator(
                regex=r'^\+?[0-9]{9,15}$',
                message=_("Format international requis (ex: +243812345678)."),
            )
        ],
    )
    is_participant = models.BooleanField(
        _("Est participant"),
        default=True,
    )

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'first_name', 'last_name', 'postnom', 'whatsapp_number']

    objects = UserManager()

    class Meta:
        verbose_name = _("Utilisateur")
        verbose_name_plural = _("Utilisateurs")
        ordering = ['last_name', 'postnom', 'first_name']

    def __str__(self):
        return f"{self.last_name} {self.postnom} {self.first_name}"

    @property
    def full_name(self):
        """Nom complet formaté : NOM Postnom Prénom."""
        return f"{self.last_name.upper()} {self.postnom} {self.first_name}"


class Profile(models.Model):
    """Profil étendu, créé automatiquement à la création du User."""

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name='profile',
    )
    created_at = models.DateTimeField(_("Créé le"), auto_now_add=True)
    updated_at = models.DateTimeField(_("Mis à jour le"), auto_now=True)
    email_verified = models.BooleanField(_("Email vérifié"), default=False)
    last_login_ip = models.GenericIPAddressField(
        _("Dernière IP de connexion"),
        null=True,
        blank=True,
    )

    class Meta:
        verbose_name = _("Profil")
        verbose_name_plural = _("Profils")

    def __str__(self):
        return f"Profil de {self.user.full_name}"