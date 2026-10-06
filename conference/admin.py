from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin

from . import translation  # noqa: F401
from .models import Conference, Speaker
from .services import activate_conference, archive_conference


class SpeakerInline(admin.StackedInline):
    """Inline pour gérer les intervenants depuis la conférence."""
    model = Speaker
    extra = 1
    fields = ('order', 'name', 'role', 'bio', 'photo', 'photo_preview', 'is_visible')
    readonly_fields = ('photo_preview',)
    show_change_link = True
    classes = ('collapse',)

    @admin.display(description=_("Aperçu"))
    def photo_preview(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="max-width:100px; max-height:100px; border-radius:50%; border:3px solid #FFD000;" />',
                obj.photo.url,
            )
        return "—"


@admin.register(Conference)
class ConferenceAdmin(TranslationAdmin):
    list_display = (
        'title', 'date', 'location', 'is_active',
        'speakers_count', 'seats_display', 'price_display_short', 'is_upcoming',
    )
    list_filter = ('is_active', 'is_free', 'date', 'created_at')
    search_fields = ('title', 'description', 'location')
    prepopulated_fields = {'slug': ('title',)}
    readonly_fields = ('created_at', 'updated_at', 'currency')
    date_hierarchy = 'date'
    inlines = [SpeakerInline]

    fieldsets = (
        (_("Informations principales"), {
            'fields': ('title', 'slug', 'organization_name', 'is_active'),
        }),
        (_("Date et lieu"), {
            'fields': ('date', 'location'),
        }),
        (_("Contenu éditorial"), {
            'fields': ('description', 'objective', 'practical_info'),
        }),
        (_("Affiche"), {
            'fields': ('poster',),
        }),
        (_("Tarification"), {
            'fields': ('is_free', 'price_per_seat', 'currency'),
        }),
        (_("Capacité"), {
            'fields': ('total_seats',),
        }),
        (_("Métadonnées"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    actions = ['activate_selected', 'archive_selected']

    @admin.display(description=_("Intervenants"))
    def speakers_count(self, obj):
        count = obj.speakers.count()
        if count == 0:
            return "—"
        return f"{count} intervenant{'s' if count > 1 else ''}"

    @admin.display(description=_("Places"))
    def seats_display(self, obj):
        if obj.total_seats == 0:
            return _("Illimité")
        return f"{obj.seats_taken} / {obj.total_seats}"

    @admin.display(description=_("Prix"))
    def price_display_short(self, obj):
        if obj.is_free:
            return _("Gratuit")
        return f"{obj.price_per_seat} {obj.currency}"

    @admin.display(description=_("À venir"), boolean=True)
    def is_upcoming(self, obj):
        return obj.is_upcoming

    @admin.action(description=_("Activer la conférence sélectionnée"))
    def activate_selected(self, request, queryset):
        if queryset.count() != 1:
            self.message_user(
                request,
                _("Veuillez sélectionner exactement une conférence."),
                level=messages.ERROR,
            )
            return
        conference = queryset.first()
        activate_conference(conference)
        self.message_user(
            request,
            _("Conférence « %(title)s » activée.") % {'title': conference.title},
            level=messages.SUCCESS,
        )

    @admin.action(description=_("Archiver la conférence sélectionnée"))
    def archive_selected(self, request, queryset):
        for conference in queryset:
            archive_conference(conference)
        self.message_user(
            request,
            _("%(count)s conférence(s) archivée(s).") % {'count': queryset.count()},
            level=messages.SUCCESS,
        )


@admin.register(Speaker)
class SpeakerAdmin(admin.ModelAdmin):
    """Admin direct pour les intervenants (indépendant des conférences)."""
    list_display = ('photo_thumb', 'name', 'role', 'conference', 'order', 'is_visible')
    list_filter = ('is_visible', 'conference')
    search_fields = ('name', 'role', 'conference__title')
    list_editable = ('order', 'is_visible')
    ordering = ('conference', 'order', 'name')
    list_per_page = 50

    fieldsets = (
        (_("Informations principales"), {
            'fields': ('title', 'slug', 'organization_name', 'is_active'),
        }),
        (_("Date et lieu"), {
            'fields': ('date', 'location'),
        }),
        (_("Contenu éditorial"), {
            'fields': ('description', 'objective', 'practical_info'),
        }),
        (_("Affiche"), {
            'fields': ('poster',),
        }),
        (_("Contacts"), {
            'fields': ('contact_phone', 'contact_email', 'contact_address'),
            'classes': ('collapse',),
        }),
        (_("Réseaux sociaux"), {
            'fields': (
                'social_facebook', 'social_instagram',
                'social_twitter', 'social_tiktok',
                'social_linkedin', 'social_youtube',
            ),
            'classes': ('collapse',),
        }),
        (_("Tarification"), {
            'fields': ('is_free', 'price_per_seat', 'currency'),
        }),
        (_("Capacité"), {
            'fields': ('total_seats',),
        }),
        (_("Métadonnées"), {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',),
        }),
    )

    readonly_fields = ('photo_thumb',)

    @admin.display(description=_("Photo"))
    def photo_thumb(self, obj):
        if obj.photo:
            return format_html(
                '<img src="{}" style="width:60px; height:60px; border-radius:50%; border:3px solid #FFD000; object-fit:cover;" />',
                obj.photo.url,
            )
        return format_html(
            '<div style="width:60px; height:60px; border-radius:50%; background:#FFD000; '
            'color:#000; display:flex; align-items:center; justify-content:center; '
            'font-weight:900; font-size:1.2rem;">{}</div>',
            obj.initials,
        )