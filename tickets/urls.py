from django.urls import path

from . import views

app_name = 'tickets'

urlpatterns = [
    # Billet individuel
    path('billet/<str:reference>/', views.ticket_detail_view, name='detail'),
    path('billet/<str:reference>/pdf/', views.ticket_download_pdf_view, name='download_pdf'),

    # Tous les billets d'une réservation
    path('reservation/<str:reference>/', views.reservation_tickets_view, name='reservation_tickets'),
    path('reservation/<str:reference>/pdf-groupe/', views.reservation_pdf_grouped_view, name='reservation_pdf_grouped'),
    path('reservation/<str:reference>/zip/', views.reservation_zip_view, name='reservation_zip'),
]