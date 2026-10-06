from django.contrib import messages
from django.http import Http404
from django.shortcuts import redirect, render
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView

from .forms import ContactForm
from .models import Conference
from .services import get_active_conference, submit_contact_form


def home_view(request):
    """
    Landing page publique.
    Affiche la conférence active ou un message si aucune.
    """
    conference = get_active_conference()

    # Compte à rebours
    days_remaining = None
    if conference and conference.is_upcoming:
        delta = conference.date - timezone.now()
        days_remaining = max(delta.days, 0)

    context = {
        'conference': conference,
        'days_remaining': days_remaining,
        'page_title': _("Accueil"),
    }
    return render(request, 'conference/home.html', context)


class ConferenceDetailView(DetailView):
    """Page de détail d'une conférence (identifiée par son slug)."""

    model = Conference
    template_name = 'conference/detail.html'
    context_object_name = 'conference'
    slug_field = 'slug'
    slug_url_kwarg = 'slug'

    def get_queryset(self):
        qs = Conference.objects.all()
        if not self.request.user.is_staff:
            qs = qs.filter(is_active=True)
        return qs

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['page_title'] = self.object.title

        if self.object.is_upcoming:
            delta = self.object.date - timezone.now()
            context['days_remaining'] = max(delta.days, 0)

        return context


def contact_view(request):
    """Page de contact avec formulaire."""
    conference = get_active_conference()

    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            success = submit_contact_form(form.cleaned_data, request=request)
            if success:
                messages.success(
                    request,
                    _("Votre message a bien été envoyé. Nous vous répondrons bientôt."),
                )
                return redirect('conference:contact')
            else:
                messages.error(
                    request,
                    _("Une erreur est survenue. Veuillez réessayer ou nous contacter directement."),
                )
    else:
        form = ContactForm()

    return render(request, 'conference/contact.html', {
        'form': form,
        'conference': conference,
        'page_title': _("Contact"),
    })