import json
import logging

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .services import handle_saspay_webhook

logger = logging.getLogger('payments')


@csrf_exempt
@require_POST
def saspay_webhook_view(request):
    """
    Reçoit les notifications SASPAY.
    NE FAIT JAMAIS CONFIANCE au contenu brut : tout est revérifié.
    """
    raw_body = request.body
    signature = request.headers.get('X-SASPAY-Signature', '')

    try:
        payload = json.loads(raw_body)
    except json.JSONDecodeError:
        logger.warning("Webhook SASPAY : payload JSON invalide.")
        return HttpResponse(status=400)

    success = handle_saspay_webhook(payload, signature, raw_body)

    if success:
        return HttpResponse(status=200)
    return HttpResponse(status=401)