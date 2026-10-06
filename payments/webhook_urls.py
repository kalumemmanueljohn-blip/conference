from django.urls import path

from . import webhooks

app_name = 'webhooks'

urlpatterns = [
    path('saspay/', webhooks.saspay_webhook_view, name='saspay'),
]