"""
Génération de QR codes.
"""
import io

import qrcode
from django.core.files.base import ContentFile


def generate_qr_image(data: str) -> ContentFile:
    """
    Génère une image PNG de QR code à partir d'une chaîne.
    Retourne un ContentFile prêt à être sauvegardé dans un ImageField.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_M,
        box_size=10,
        border=2,
    )
    qr.add_data(data)
    qr.make(fit=True)

    img = qr.make_image(fill_color="black", back_color="white")

    buffer = io.BytesIO()
    img.save(buffer, format='PNG')
    return ContentFile(buffer.getvalue())