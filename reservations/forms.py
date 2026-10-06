from django import forms
from django.utils.translation import gettext_lazy as _

from conference.models import Conference


class ReservationForm(forms.Form):
    """Formulaire de création/modification d'une réservation."""

    seats = forms.IntegerField(
        label=_("Nombre de places"),
        min_value=1,
        max_value=5,
        initial=1,
        widget=forms.NumberInput(attrs={
            'class': 'form-control',
            'min': 1,
            'max': 5,
        }),
        help_text=_("Entre 1 et 5 places par réservation."),
    )

    payment_phone_number = forms.CharField(
        label=_("Numéro mobile money à débiter"),
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '+243 81 234 5678',
        }),
        help_text=_(
            "Le numéro qui recevra la demande de paiement (Vodacom M-Pesa, "
            "Airtel Money, ou Orange Money). Laissez vide pour utiliser votre "
            "numéro WhatsApp par défaut."
        ),
    )

    def __init__(self, *args, conference: Conference = None, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.conference = conference
        self.user = user

        # Pré-remplir avec le WhatsApp du user
        if user and not self.is_bound:
            self.fields['payment_phone_number'].initial = user.whatsapp_number

        if conference and conference.total_seats > 0:
            remaining = conference.seats_remaining
            max_seats = min(5, remaining)
            self.fields['seats'].widget.attrs['max'] = max_seats
            self.fields['seats'].validators[0].limit_value = max_seats

    def clean_seats(self):
        seats = self.cleaned_data['seats']
        if self.conference and self.conference.total_seats > 0:
            if seats > self.conference.seats_remaining:
                raise forms.ValidationError(
                    _("Il ne reste que %(remaining)s place(s) disponible(s).") % {
                        'remaining': self.conference.seats_remaining
                    }
                )
        return seats

    def clean_payment_phone_number(self):
        phone = self.cleaned_data.get('payment_phone_number', '').strip()
        if not phone:
            # Fallback sur le WhatsApp du user
            if self.user:
                return self.user.whatsapp_number
            raise forms.ValidationError(
                _("Veuillez renseigner un numéro mobile money.")
            )
        return phone