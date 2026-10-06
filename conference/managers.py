from django.db import models


class ConferenceQuerySet(models.QuerySet):
    """QuerySet personnalisé pour Conference."""

    def active(self):
        """Retourne la conférence actuellement active."""
        return self.filter(is_active=True)

    def upcoming(self):
        """Retourne les conférences à venir (date future), triées par date."""
        from django.utils import timezone
        return self.filter(date__gte=timezone.now()).order_by('date')


class ConferenceManager(models.Manager):
    """Manager custom pour Conference."""

    def get_queryset(self):
        return ConferenceQuerySet(self.model, using=self._db)

    def get_active(self):
        """
        Retourne l'unique conférence active.
        Retourne None si aucune conférence n'est active.
        """
        return self.get_queryset().active().first()

    def active(self):
        """Raccourci pour get_queryset().active()."""
        return self.get_queryset().active()