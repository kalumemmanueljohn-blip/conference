"""
Client API SASPAY (api.saspay.me)
Authentification : Bearer Token (clé sk_live_... ou sk_test_...)
Docs : https://docs.saspay.app
"""
import hashlib
import hmac
import logging
import uuid

import requests
from django.conf import settings

logger = logging.getLogger('payments')


class SaspayError(Exception):
    """Exception métier SASPAY."""
    pass


class SaspayClient:
    """Client isolé pour l'API SASPAY."""

    def __init__(self):
        self.api_key = settings.SASPAY_API_KEY
        self.base_url = settings.SASPAY_BASE_URL.rstrip('/') if settings.SASPAY_BASE_URL else ''
        self.webhook_secret = settings.SASPAY_WEBHOOK_SECRET
        self.timeout = 30

    def _headers(self, idempotency_key=None):
        """Headers d'authentification SASPAY."""
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json',
            'Accept': 'application/json',
        }
        if idempotency_key:
            headers['Idempotency-Key'] = idempotency_key
        return headers

    # ============================================================
    # CRÉER UNE TRANSACTION (Softpay - push mobile money USD)
    # ============================================================

    def create_transaction(self, reservation, payment) -> dict:
        """
        Crée une transaction SASPAY via Softpay (push mobile money).

        Endpoint : POST /api/v1/payments/softpay/
        Pays     : XC (RDC USD)
        Devise   : USD
        Réseaux  : vodacom_cd_usd, airtel_cd_usd, orange_cd_usd
        """
        if not self.api_key or not self.base_url:
            raise SaspayError(
                "Configuration SASPAY incomplète : "
                "SASPAY_API_KEY et SASPAY_BASE_URL sont requis."
            )

        # Réseau choisi par l'utilisateur (fallback sur défaut)
        network = (
            reservation.saspay_network
            or getattr(settings, 'SASPAY_DEFAULT_NETWORK', 'vodacom_cd_usd')
        )

        endpoint = "/api/v1/payments/softpay/"
        url = f"{self.base_url}{endpoint}"

        payload = {
            "amount": str(payment.amount),
            "currency": "USD",
            "country": "XC",
            "network": network,
            "description": f"Réservation {reservation.reference}",
            "customer": {
                "email": reservation.user.email,
                "first_name": reservation.user.first_name or "Client",
                "last_name": reservation.user.last_name or "Bantondo",
                "phone": reservation.user.whatsapp_number,
            }
        }

        # Idempotency-Key : évite les doublons en cas de retry réseau
        idempotency_key = str(uuid.uuid4())

        try:
            response = requests.post(
                url,
                json=payload,
                headers=self._headers(idempotency_key),
                timeout=self.timeout,
            )
            response.raise_for_status()
            data = response.json()
            logger.info(
                f"SASPAY create_transaction OK : "
                f"id={data.get('id')} network={network}"
            )
            return data

        except requests.RequestException as e:
            logger.error(f"Erreur SASPAY create_transaction : {e}")
            raise SaspayError(f"Erreur SASPAY : {e}") from e

    # ============================================================
    # VÉRIFIER UNE TRANSACTION
    # ============================================================

    def verify_transaction(self, transaction_id: str) -> dict:
        """
        Vérifie une transaction côté serveur.

        Endpoint : GET /api/v1/payments/<id>/verify/
        """
        if not self.api_key or not self.base_url:
            raise SaspayError("Configuration SASPAY incomplète.")

        endpoint = f"/api/v1/payments/{transaction_id}/verify/"
        url = f"{self.base_url}{endpoint}"

        try:
            response = requests.get(
                url,
                headers=self._headers(),
                timeout=self.timeout,
            )
            response.raise_for_status()
            return response.json()

        except requests.RequestException as e:
            logger.error(f"Erreur SASPAY verify_transaction : {e}")
            raise SaspayError(f"Erreur SASPAY : {e}") from e

    # ============================================================
    # VÉRIFIER SIGNATURE WEBHOOK
    # ============================================================

    def verify_webhook_signature(self, payload: bytes, signature: str) -> bool:
        """
        Vérifie la signature HMAC du webhook SASPAY.
        Algorithme : HMAC-SHA256 (à confirmer selon la doc webhooks SASPAY).
        """
        if not self.webhook_secret:
            logger.error("SASPAY_WEBHOOK_SECRET manquant.")
            return False

        if not signature:
            return False

        expected = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()

        return hmac.compare_digest(expected, signature)