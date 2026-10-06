from django.urls import path

from . import views

app_name = 'dashboard'

urlpatterns = [
    # Dashboard principal
    path('', views.dashboard_home_view, name='home'),

    # Recherche
    path('recherche/', views.dashboard_search_view, name='search'),

    # Contrôle à l'entrée
    path('controle/', views.checkin_view, name='checkin'),
    path('controle/<str:reference>/valider/', views.checkin_confirm_view, name='checkin_confirm'),

    # Validation WhatsApp
    path('whatsapp/', views.whatsapp_proofs_list_view, name='whatsapp_proofs'),
    path('whatsapp/<int:proof_id>/', views.whatsapp_proof_detail_view, name='whatsapp_proof_detail'),
    path('whatsapp/<int:proof_id>/valider/', views.whatsapp_proof_validate_view, name='whatsapp_proof_validate'),
    path('whatsapp/<int:proof_id>/rejeter/', views.whatsapp_proof_reject_view, name='whatsapp_proof_reject'),
]