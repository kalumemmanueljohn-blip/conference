from django.urls import path

from . import views

app_name = 'payments'

urlpatterns = [
    path('<str:reference>/', views.choose_payment_view, name='choose'),
    path('<str:reference>/saspay/', views.saspay_init_view, name='saspay_init'),
    path('<str:reference>/whatsapp/', views.whatsapp_init_view, name='whatsapp_init'),
]