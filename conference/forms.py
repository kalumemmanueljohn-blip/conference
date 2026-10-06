from django import forms
from django.utils.translation import gettext_lazy as _


class ContactForm(forms.Form):
    """Formulaire de contact public."""

    name = forms.CharField(
        label=_("Votre nom complet"),
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _("Ex: Jean KABILA"),
        }),
    )
    email = forms.EmailField(
        label=_("Votre email"),
        widget=forms.EmailInput(attrs={
            'class': 'form-control',
            'placeholder': _("vous@example.com"),
        }),
    )
    phone = forms.CharField(
        label=_("Téléphone (optionnel)"),
        max_length=30,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _("+243..."),
        }),
    )
    subject = forms.CharField(
        label=_("Sujet"),
        max_length=200,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': _("Objet de votre message"),
        }),
    )
    message = forms.CharField(
        label=_("Message"),
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 6,
            'placeholder': _("Votre message..."),
        }),
    )

    # Honeypot anti-spam (caché en CSS)
    website = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'hp-field',
            'autocomplete': 'off',
            'tabindex': '-1',
        }),
    )

    def clean_website(self):
        """Si le champ honeypot est rempli, c'est un bot."""
        value = self.cleaned_data.get('website', '')
        if value:
            raise forms.ValidationError(_("Erreur de validation."))
        return value