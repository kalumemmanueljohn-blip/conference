from django.urls import path

from . import views

app_name = 'accounts'

urlpatterns = [
    # Inscription / connexion / déconnexion
    path('inscription/', views.RegisterView.as_view(), name='register'),
    path('connexion/', views.login_view, name='login'),
    path('deconnexion/', views.logout_view, name='logout'),

    # Espace participant
    path('espace/', views.dashboard_view, name='dashboard'),
    path('espace/profil/', views.profile_view, name='profile'),
    path('espace/mot-de-passe/', views.password_change_view, name='password_change'),

    # Réinitialisation mot de passe
    path('mot-de-passe-oublie/', views.CustomPasswordResetView.as_view(), name='password_reset'),
    path('mot-de-passe-oublie/envoye/', views.CustomPasswordResetDoneView.as_view(), name='password_reset_done'),
    path('mot-de-passe/reinitialiser/<uidb64>/<token>/', views.CustomPasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('mot-de-passe/reinitialise/', views.CustomPasswordResetCompleteView.as_view(), name='password_reset_complete'),
]