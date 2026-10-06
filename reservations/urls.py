from django.urls import path

from . import views

app_name = 'reservations'

urlpatterns = [
    path('', views.my_reservations_view, name='list'),
    path('nouvelle/', views.create_reservation_view, name='create'),
    path('<str:reference>/', views.reservation_detail_view, name='detail'),
    path('<str:reference>/annuler/', views.cancel_reservation_view, name='cancel'),
]