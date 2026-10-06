from django.urls import path

from . import views

app_name = 'conference'

urlpatterns = [
    path('', views.home_view, name='home'),
    path('contact/', views.contact_view, name='contact'),
    path('conference/<slug:slug>/', views.ConferenceDetailView.as_view(), name='detail'),
]