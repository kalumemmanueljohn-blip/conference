from django.contrib import messages
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import (
    PasswordResetCompleteView,
    PasswordResetConfirmView,
    PasswordResetDoneView,
    PasswordResetView,
)
from django.shortcuts import redirect, render
from django.urls import reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import CreateView
from notifications.services import send_welcome_email
from .forms import (
    CustomPasswordChangeForm,
    LoginForm,
    ProfileUpdateForm,
    RegistrationForm,
)

class RegisterView(CreateView):
    """Inscription d'un nouveau participant."""

    form_class = RegistrationForm
    template_name = 'accounts/register.html'
    success_url = reverse_lazy('accounts:dashboard')

    def form_valid(self, form):
        response = super().form_valid(form)
        login(self.request, self.object)
        messages.success(self.request, _("Votre compte a été créé avec succès."))

        # Envoi email de bienvenue (silencieux en cas d'erreur)
        try:
            from notifications.services import send_welcome_email
            send_welcome_email(self.object)
        except Exception:
            pass

        return response



def login_view(request):
    """Connexion par email."""
    if request.user.is_authenticated:
        return redirect('accounts:dashboard')

    form = LoginForm(request, data=request.POST or None)
    if request.method == 'POST' and form.is_valid():
        login(request, form.get_user())
        messages.success(request, _("Connexion réussie."))
        return redirect(request.GET.get('next') or 'accounts:dashboard')

    return render(request, 'accounts/login.html', {'form': form})


def logout_view(request):
    """Déconnexion."""
    logout(request)
    messages.info(request, _("Vous êtes déconnecté."))
    return redirect('conference:home')


@login_required
def dashboard_view(request):
    """Espace participant : résumé."""
    return render(request, 'accounts/dashboard.html', {'user': request.user})


@login_required
def profile_view(request):
    """Consultation et mise à jour du profil."""
    form = ProfileUpdateForm(request.POST or None, instance=request.user)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Profil mis à jour."))
        return redirect('accounts:profile')
    return render(request, 'accounts/profile.html', {'form': form})


@login_required
def password_change_view(request):
    """Changement de mot de passe."""
    form = CustomPasswordChangeForm(request.user, request.POST or None)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, _("Mot de passe modifié."))
        return redirect('accounts:profile')
    return render(request, 'accounts/password_change.html', {'form': form})


# ===== Réinitialisation mot de passe =====

class CustomPasswordResetView(PasswordResetView):
    template_name = 'accounts/password_reset.html'
    email_template_name = 'accounts/emails/password_reset.txt'
    subject_template_name = 'accounts/emails/password_reset_subject.txt'
    success_url = reverse_lazy('accounts:password_reset_done')


class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'accounts/password_reset_done.html'


class CustomPasswordResetConfirmView(PasswordResetConfirmView):
    template_name = 'accounts/password_reset_confirm.html'
    success_url = reverse_lazy('accounts:password_reset_complete')


class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'accounts/password_reset_complete.html'