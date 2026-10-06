from django.conf import settings
from django.conf.urls.static import static
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.urls import include, path
from django.utils.translation import gettext_lazy as _

# ============================================================
# URLS NON TRADUITES (webhooks, admin, i18n switch)
# ============================================================
urlpatterns = [
    path('admin/', admin.site.urls),
    path('i18n/', include('django.conf.urls.i18n')),          # changement de langue
    # Webhooks SASPAY : URL fixe, jamais traduite
    path('webhooks/', include('payments.webhook_urls', namespace='webhooks')),
]

# ============================================================
# URLS TRADUITES FR / EN
# FR : sans préfixe  → /compte/connexion/
# EN : avec préfixe  → /en/account/login/
# ============================================================
urlpatterns += i18n_patterns(
    path('', include('conference.urls', namespace='conference')),
    path(_('compte/'), include('accounts.urls', namespace='accounts')),
    path(_('reservations/'), include('reservations.urls', namespace='reservations')),
    path(_('paiements/'), include('payments.urls', namespace='payments')),
    path(_('billets/'), include('tickets.urls', namespace='tickets')),
    path(_('dashboard/'), include('dashboard.urls', namespace='dashboard')),
    prefix_default_language=False,
)

# ============================================================
# MÉDIAS EN DEV
# ============================================================
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)