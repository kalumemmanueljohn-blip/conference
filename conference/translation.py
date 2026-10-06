"""
Configuration modeltranslation pour l'app conference.
"""
from modeltranslation.translator import TranslationOptions, register

from .models import Conference, Speaker


@register(Conference)
class ConferenceTranslationOptions(TranslationOptions):
    fields = (
        'title',
        'description',
        'objective',
        'practical_info',
        'location',
    )


@register(Speaker)
class SpeakerTranslationOptions(TranslationOptions):
    fields = (
        'role',
        'bio',
    )