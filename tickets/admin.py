from django.contrib import admin
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Ticket


@admin.register(Ticket)
class TicketAdmin(admin.ModelAdmin):
    list_display = (
        'ticket_reference', 'seat_display', 'user_display',
        'conference_display', 'status', 'generated_at', 'used_at',
    )
    list_filter = ('status', 'generated_at', 'used_at')
    search_fields = (
        'ticket_reference',
        'reservation__reference',
        'reservation__user__email',
        'reservation__user__last_name',
        'reservation__user__postnom',
        'qr_token',
    )
    readonly_fields = (
        'ticket_reference', 'seat_number', 'qr_token',
        'qr_image_preview', 'pdf_file',
        'generated_at', 'used_at', 'checked_by',
    )
    date_hierarchy = 'generated_at'
    list_per_page = 50

    fieldsets = (
        (_("Identification"), {
            'fields': ('ticket_reference', 'seat_number', 'reservation'),
        }),
        (_("QR"), {
            'fields': ('qr_token', 'qr_image_preview'),
        }),
        (_("PDF"), {
            'fields': ('pdf_file',),
        }),
        (_("Contrôle"), {
            'fields': ('status', 'generated_at', 'used_at', 'checked_by'),
        }),
    )

    @admin.display(description=_("Place"), ordering='seat_number')
    def seat_display(self, obj):
        return f"{obj.seat_number}/{obj.reservation.seats}"

    @admin.display(description=_("Participant"), ordering='reservation__user__last_name')
    def user_display(self, obj):
        return obj.reservation.user.full_name

    @admin.display(description=_("Conférence"))
    def conference_display(self, obj):
        return obj.reservation.conference.title

    @admin.display(description=_("Aperçu QR"))
    def qr_image_preview(self, obj):
        if obj.qr_image:
            return format_html(
                '<img src="{}" style="max-width:150px; max-height:150px;" />',
                obj.qr_image.url,
            )
        return "—"