"""
Génération des PDF de billets (individuels + groupé).
"""
import io
import logging

from django.conf import settings
from django.template.loader import render_to_string
from django.utils import timezone

logger = logging.getLogger('tickets')


def _build_context(ticket):
    """Prépare le contexte pour le template."""
    reservation = ticket.reservation
    conference = reservation.conference

    # QR en chemin absolu
    qr_url = ''
    if ticket.qr_image:
        try:
            qr_path = ticket.qr_image.path
            qr_url = f"file:///{qr_path.replace(chr(92), '/')}"
        except Exception as e:
            logger.error(f"Erreur chemin QR : {e}")

    # Logo en chemin absolu
    logo_url = ''
    logo_path = settings.BASE_DIR / 'static' / 'images' / 'logo.png'
    if logo_path.exists():
        logo_url = f"file:///{str(logo_path).replace(chr(92), '/')}"

    return {
        'ticket': ticket,
        'reservation': reservation,
        'conference': conference,
        'user': reservation.user,
        'qr_url': qr_url,
        'logo_url': logo_url,
        'generated_at': timezone.now(),
    }


def _weasyprint():
    try:
        from weasyprint import HTML, CSS
        return HTML, CSS
    except ImportError:
        raise RuntimeError(
            "WeasyPrint n'est pas installé. Installez-le : pip install weasyprint"
        )


def generate_ticket_pdf(ticket) -> bytes:
    """
    Génère le PDF d'UN billet individuel (format A5).
    """
    HTML, CSS = _weasyprint()

    context = _build_context(ticket)
    html_string = render_to_string('tickets/ticket_a5.html', context)

    css = CSS(string='@page { size: A5; margin: 0; }')

    pdf_buffer = io.BytesIO()
    HTML(string=html_string, base_url=str(settings.BASE_DIR)).write_pdf(
        pdf_buffer, stylesheets=[css],
    )
    logger.info(f"PDF généré pour billet {ticket.ticket_reference}")
    return pdf_buffer.getvalue()


def generate_grouped_pdf(reservation) -> bytes:
    """
    Génère le PDF groupé : N billets dans un seul fichier.
    Chaque billet occupe une page A5 indépendante.

    Utilise pypdf pour fusionner les PDF individuels proprement,
    garantissant que le CSS de chaque billet est bien appliqué.
    """
    HTML, CSS = _weasyprint()

    tickets = reservation.tickets.order_by('seat_number')
    if not tickets.exists():
        raise RuntimeError("Aucun billet à inclure dans le PDF groupé.")

    # Essayer d'utiliser pypdf (méthode propre)
    try:
        from pypdf import PdfWriter, PdfReader
        use_pypdf = True
    except ImportError:
        use_pypdf = False
        logger.warning(
            "pypdf n'est pas installé. Le PDF groupé peut avoir un design "
            "incorrect. Installez-le : pip install pypdf"
        )

    css = CSS(string='@page { size: A5; margin: 0; }')

    # ---- Méthode 1 : pypdf (recommandée) ----
    if use_pypdf:
        writer = PdfWriter()

        for ticket in tickets:
            context = _build_context(ticket)
            html_string = render_to_string('tickets/ticket_a5.html', context)

            pdf_buffer = io.BytesIO()
            HTML(
                string=html_string,
                base_url=str(settings.BASE_DIR),
            ).write_pdf(pdf_buffer, stylesheets=[css])
            pdf_buffer.seek(0)

            # Ajouter chaque page du billet au document final
            reader = PdfReader(pdf_buffer)
            for page in reader.pages:
                writer.add_page(page)

        output_buffer = io.BytesIO()
        writer.write(output_buffer)
        output_buffer.seek(0)

        logger.info(
            f"PDF groupé généré pour {reservation.reference} "
            f"({tickets.count()} billets) [pypdf]"
        )
        return output_buffer.getvalue()

    # ---- Méthode 2 : fusion HTML (fallback) ----
    # On garde le CSS COMPLET du premier billet
    html_parts = []
    for ticket in tickets:
        context = _build_context(ticket)
        context['is_grouped'] = True
        context['total_tickets'] = tickets.count()
        html_parts.append(
            render_to_string('tickets/ticket_a5.html', context)
        )

    # Extraire le contenu du body de chaque billet
    first_html = html_parts[0]
    other_bodies = []
    for part in html_parts[1:]:
        if '<body>' in part and '</body>' in part:
            body = part.split('<body>')[1].split('</body>')[0]
            other_bodies.append(body)

    # Fusionner : garder le 1er HTML entier (avec CSS),
    # et ajouter les autres bodies avec saut de page
    if other_bodies:
        additional = ''.join(
            f'<div class="page-break-section">{body}</div>'
            for body in other_bodies
        )
        full_html = first_html.replace('</body>', f'{additional}</body>')
    else:
        full_html = first_html

    # Ajouter le CSS de saut de page
    full_html = full_html.replace(
        '</head>',
        '<style>.page-break-section { page-break-before: always; }</style></head>',
    )

    pdf_buffer = io.BytesIO()
    HTML(
        string=full_html,
        base_url=str(settings.BASE_DIR),
    ).write_pdf(pdf_buffer, stylesheets=[css])

    logger.info(
        f"PDF groupé généré pour {reservation.reference} "
        f"({tickets.count()} billets) [fusion HTML]"
    )
    return pdf_buffer.getvalue()