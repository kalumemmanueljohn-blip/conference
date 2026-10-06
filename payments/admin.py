from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _

from .models import Payment, SaspayTransaction, WhatsappProof
from .services import (
    reject_whatsapp_payment,
    request_new_whatsapp_proof,
    validate_whatsapp_payment,
)


@admin.register(Payment)
class PaymentAdmin(admin.ModelAdmin):
    list_display = (
        'internal_reference', 'reservation_link', 'method',
        'amount_display', 'status', 'created_at', 'confirmed_at',
    )
    list_filter = ('method', 'status', 'created_at')
    search_fields = (
        'internal_reference',
        'reservation__reference',
        'reservation__user__email',
    )
    readonly_fields = (
        'internal_reference', 'currency',
        'created_at', 'updated_at', 'confirmed_at',
    )
    date_hierarchy = 'created_at'

    @admin.display(description=_("Réservation"))
    def reservation_link(self, obj):
        return obj.reservation.reference

    @admin.display(description=_("Montant"))
    def amount_display(self, obj):
        return f"{obj.amount} {obj.currency}"


@admin.register(SaspayTransaction)
class SaspayTransactionAdmin(admin.ModelAdmin):
    list_display = (
        'payment', 'saspay_transaction_id', 'saspay_reference',
        'signature_verified', 'verified_at',
    )
    list_filter = ('signature_verified',)
    search_fields = ('saspay_transaction_id', 'saspay_reference', 'payment__internal_reference')
    readonly_fields = (
        'payment', 'saspay_transaction_id', 'saspay_reference',
        'raw_request', 'raw_response', 'signature_verified', 'verified_at',
    )


@admin.register(WhatsappProof)
class WhatsappProofAdmin(admin.ModelAdmin):
    list_display = (
        'payment', 'user_display', 'status', 'uploaded_at',
        'validated_by', 'validated_at',
    )
    list_filter = ('status', 'uploaded_at')
    search_fields = ('payment__internal_reference', 'payment__reservation__reference')
    readonly_fields = ('uploaded_at', 'validated_at', 'proof_preview')
    actions = ['validate_selected', 'reject_selected', 'request_new_proof']

    fieldsets = (
        (_("Informations"), {
            'fields': ('payment', 'status', 'uploaded_at', 'validated_by', 'validated_at')
        }),
        (_("Preuve"), {
            'fields': ('proof_file', 'proof_preview')
        }),
        (_("Rejet"), {
            'fields': ('rejection_reason',),
            'classes': ('collapse',),
        }),
    )

    @admin.display(description=_("Participant"))
    def user_display(self, obj):
        return obj.payment.reservation.user.full_name

    @admin.display(description=_("Aperçu"))
    def proof_preview(self, obj):
        if not obj.proof_file:
            return "—"
        url = obj.proof_file.url
        name = obj.proof_file.name.lower()
        if name.endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            return format_html(
                '<a href="{}" target="_blank"><img src="{}" style="max-width:400px; max-height:400px; border-radius:8px; border:2px solid #d6a63a;"></a>',
                url, url,
            )
        return format_html('<a href="{}" target="_blank">Télécharger le fichier</a>', url)

    @admin.action(description=_("Valider les preuves sélectionnées"))
    def validate_selected(self, request, queryset):
        count = 0
        for proof in queryset.filter(status__in=['pending', 'new_proof_requested']):
            try:
                validate_whatsapp_payment(proof, request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f"Erreur sur {proof} : {e}", level=messages.ERROR)
        if count:
            self.message_user(
                request,
                _("%(count)s preuve(s) validée(s). Billets générés et emails envoyés.") % {'count': count},
                level=messages.SUCCESS,
            )

    @admin.action(description=_("Rejeter les preuves sélectionnées"))
    def reject_selected(self, request, queryset):
        count = 0
        for proof in queryset.filter(status__in=['pending', 'new_proof_requested']):
            try:
                reject_whatsapp_payment(proof, request.user, reason="Rejeté depuis l'admin")
                count += 1
            except Exception as e:
                self.message_user(request, f"Erreur sur {proof} : {e}", level=messages.ERROR)
        if count:
            self.message_user(
                request,
                _("%(count)s preuve(s) rejetée(s).") % {'count': count},
                level=messages.SUCCESS,
            )

    @admin.action(description=_("Demander une nouvelle preuve"))
    def request_new_proof(self, request, queryset):
        count = 0
        for proof in queryset.filter(status__in=['pending', 'new_proof_requested']):
            try:
                request_new_whatsapp_proof(proof, request.user)
                count += 1
            except Exception as e:
                self.message_user(request, f"Erreur sur {proof} : {e}", level=messages.ERROR)
        if count:
            self.message_user(
                request,
                _("%(count)s nouvelle(s) preuve(s) demandée(s).") % {'count': count},
                level=messages.SUCCESS,
            )