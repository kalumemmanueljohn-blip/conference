from django.contrib import admin
from django.utils.translation import gettext_lazy as _

from .models import Reservation


@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = (
        'reference', 'user_display', 'conference',
        'seats', 'total_amount_display', 'status',
        'payment_method', 'created_at',
    )
    list_filter = ('status', 'payment_method', 'conference', 'created_at')
    search_fields = (
        'reference',
        'user__email', 'user__last_name', 'user__postnom', 'user__first_name',
        'user__whatsapp_number',
    )
    readonly_fields = (
        'reference', 'created_at', 'updated_at',
        'confirmed_at', 'cancelled_at', 'currency',
    )
    date_hierarchy = 'created_at'
    list_per_page = 50

    fieldsets = (
        (_("Identification"), {
            'fields': ('reference', 'user', 'conference'),
        }),
        (_("Détails"), {
            'fields': ('seats', 'total_amount', 'currency', 'status', 'payment_method'),
        }),
        (_("Dates"), {
            'fields': ('created_at', 'updated_at', 'confirmed_at', 'cancelled_at'),
        }),
    )

    @admin.display(description=_("Utilisateur"), ordering='user__last_name')
    def user_display(self, obj):
        return obj.user.full_name

    @admin.display(description=_("Montant"))
    def total_amount_display(self, obj):
        if obj.total_amount == 0:
            return _("Gratuit")
        return f"{obj.total_amount} {obj.currency}"