import logging

from django.utils import timezone

from .models import Conference

logger = logging.getLogger('reservations')


def get_active_conference() -> Conference | None:
    """
    Récupère la conférence active.
    Retourne None si aucune conférence n'est active.
    """
    return Conference.objects.get_active()


def activate_conference(conference: Conference) -> Conference:
    """
    Active une conférence et désactive automatiquement toutes les autres.
    L'opération est atomique.
    """
    from django.db import transaction

    with transaction.atomic():
        # Désactiver les autres
        Conference.objects.exclude(pk=conference.pk).filter(is_active=True).update(is_active=False)
        # Activer celle-ci
        conference.is_active = True
        conference.save(update_fields=['is_active', 'updated_at'])

    logger.info(f"Conférence activée : {conference.title}")
    return conference


def archive_conference(conference: Conference) -> Conference:
    """Archive une conférence (désactive)."""
    conference.is_active = False
    conference.save(update_fields=['is_active', 'updated_at'])
    logger.info(f"Conférence archivée : {conference.title}")
    return conference


def is_conference_open_for_reservation(conference: Conference) -> bool:
    """
    Vérifie si la conférence accepte encore des réservations.
    Règles :
    - Doit être active
    - Doit être dans le futur
    - Ne doit pas être complète
    """
    if not conference.is_active:
        return False
    if conference.is_past:
        return False
    if conference.is_full:
        return False
    return True

def submit_contact_form(form_data, request=None):
    """
    Traite la soumission d'un formulaire de contact.
    Envoie un email à l'organisation.
    """
    from notifications.services import send_contact_email

    conference = get_active_conference()
    success = send_contact_email(form_data, conference=conference)

    if success:
        logger.info(f"Formulaire de contact soumis par {form_data['email']}")
    else:
        logger.error(f"Échec envoi formulaire contact par {form_data['email']}")

    return success