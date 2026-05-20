from __future__ import annotations

import base64
import io
import os
import re
from datetime import timedelta
from typing import Any

from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import Image, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from PIL import Image as PILImage

from core.models import Application, OfferWorkflow
from core.workflow import now_utc, offer_storage_root


def _safe_name(value: str, fallback: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9._-]+", "_", value or "").strip("._")
    return clean or fallback


def _ensure_offer_folder(offer: OfferWorkflow) -> str:
    folder = os.path.join(offer_storage_root(), str(offer.application_id))
    os.makedirs(folder, exist_ok=True)
    return folder


def _data_url_to_bytes(data_url: str) -> bytes:
    if not data_url:
        return b""
    raw = data_url.split(",", 1)[1] if data_url.startswith("data:") and "," in data_url else data_url
    return base64.b64decode(raw)


def persist_signature_image(offer: OfferWorkflow, *, data_url: str, filename: str = "signature.png") -> str:
    folder = _ensure_offer_folder(offer)
    safe_name = _safe_name(filename, "signature.png")
    path = os.path.join(folder, safe_name)
    payload = _data_url_to_bytes(data_url)
    image = PILImage.open(io.BytesIO(payload))
    image.save(path)
    return path


def _styles():
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "OfferTitle",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=20,
            leading=24,
            textColor=colors.HexColor("#111111"),
            spaceAfter=12,
        ),
        "eyebrow": ParagraphStyle(
            "OfferEyebrow",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=10,
            leading=12,
            textColor=colors.HexColor("#ff5a0d"),
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "OfferBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=10.5,
            leading=16,
            textColor=colors.HexColor("#2f2f2f"),
            alignment=TA_LEFT,
            spaceAfter=8,
        ),
        "section": ParagraphStyle(
            "OfferSection",
            parent=base["Heading2"],
            fontName="Helvetica-Bold",
            fontSize=12,
            leading=16,
            textColor=colors.HexColor("#111111"),
            spaceBefore=10,
            spaceAfter=8,
        ),
        "small": ParagraphStyle(
            "OfferSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=colors.HexColor("#666666"),
            spaceAfter=6,
        ),
    }


def _offer_rows(application: Application, offer: OfferWorkflow) -> list[list[str]]:
    return [
        ["Candidate", application.full_name or "Candidate"],
        ["Role", offer.designation or application.current_title or "Role"],
        ["Department", offer.department or "Team"],
        ["Employment Type", offer.employment_type or "Not specified"],
        ["Compensation", offer.offered_compensation or offer.compensation_text or "As discussed"],
        ["Compensation Notes", offer.compensation_text or "Not specified"],
        ["Contract Notes", offer.contract_duration_or_notes or "Not applicable"],
        ["Joining Date", offer.joining_date or "To be confirmed"],
        ["Offer Valid Until", offer.offer_valid_until or "Not specified"],
        ["Work Mode", offer.work_mode or "Not specified"],
        ["Work Location", offer.work_location or application.location or "Not specified"],
        ["Reporting Manager", offer.reporting_manager or "To be confirmed"],
        ["Reporting Team", offer.reporting_team or "To be confirmed"],
        ["HR Contact", offer.hr_contact_details or "HR Team"],
    ]


def generate_offer_pdf(
    application: Application,
    offer: OfferWorkflow,
    *,
    signed: bool = False,
    signature_path: str | None = None,
) -> str:
    folder = _ensure_offer_folder(offer)
    filename = "offer_letter_signed.pdf" if signed else "offer_letter_unsigned.pdf"
    path = os.path.join(folder, filename)
    styles = _styles()
    doc = SimpleDocTemplate(
        path,
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
    )

    story: list[Any] = []
    story.append(Paragraph("Hiresy Offer Letter", styles["eyebrow"]))
    story.append(Paragraph(f"Offer of Employment — {offer.designation or application.current_title or 'Role'}", styles["title"]))
    story.append(
        Paragraph(
            (
                f"Dear <b>{application.full_name or 'Candidate'}</b>,<br/>"
                f"We are pleased to extend an offer for the position of "
                f"<b>{offer.designation or application.current_title or 'Role'}</b>. "
                f"This letter summarizes the proposed employment details and next steps."
            ),
            styles["body"],
        )
    )
    story.append(Spacer(1, 6))

    rows = _offer_rows(application, offer)
    table = Table(rows, colWidths=[42 * mm, 120 * mm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#fff4ee")),
                ("TEXTCOLOR", (0, 0), (-1, -1), colors.HexColor("#222222")),
                ("FONTNAME", (0, 0), (-1, -1), "Helvetica"),
                ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9.5),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#dddddd")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("TOPPADDING", (0, 0), (-1, -1), 8),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
            ]
        )
    )
    story.append(table)
    story.append(Spacer(1, 10))

    story.append(Paragraph("Joining Instructions", styles["section"]))
    story.append(Paragraph(offer.onboarding_instructions or "Please coordinate with HR for onboarding readiness, equipment, and reporting instructions.", styles["body"]))

    story.append(Paragraph("Company Details", styles["section"]))
    story.append(Paragraph(offer.company_details or "Hiresy Recruiting Platform", styles["body"]))

    story.append(Paragraph("Terms and Conditions", styles["section"]))
    story.append(Paragraph(offer.terms_and_conditions or "This offer is contingent upon successful verification, acceptance of company policies, and completion of all joining formalities.", styles["body"]))

    if signed:
        story.append(Paragraph("Candidate Response", styles["section"]))
        response_label = "Accepted" if offer.candidate_response == "accepted" else "Rejected"
        story.append(Paragraph(f"Response: <b>{response_label}</b>", styles["body"]))
        if offer.candidate_remarks:
            story.append(Paragraph(f"Candidate Remarks: {offer.candidate_remarks}", styles["body"]))
        story.append(Paragraph(f"Submitted At: {offer.candidate_response_at.isoformat() if offer.candidate_response_at else 'Not recorded'}", styles["small"]))
        story.append(Paragraph(f"IP / Device: {offer.candidate_ip or 'Unknown'} / {offer.candidate_user_agent or 'Unknown device'}", styles["small"]))
        if signature_path and os.path.exists(signature_path):
            story.append(Spacer(1, 6))
            story.append(Paragraph("Digital Signature", styles["section"]))
            image = Image(signature_path)
            image.drawHeight = 25 * mm
            image.drawWidth = 60 * mm
            story.append(image)

    story.append(Spacer(1, 12))
    story.append(Paragraph("Authorized by Hiresy HR", styles["small"]))
    story.append(Paragraph(f"Generated at {now_utc().isoformat()}", styles["small"]))
    doc.build(story)
    return path


def refresh_offer_documents(application: Application, offer: OfferWorkflow) -> tuple[str, str | None]:
    unsigned_path = generate_offer_pdf(application, offer, signed=False)
    signed_path = None
    if offer.candidate_response == "accepted" and offer.signature_image_path:
        signed_path = generate_offer_pdf(
            application,
            offer,
            signed=True,
            signature_path=offer.signature_image_path,
        )
    return unsigned_path, signed_path


def reset_offer_expiry(offer: OfferWorkflow, *, days: int = 7) -> None:
    offer.candidate_portal_expires_at = now_utc() + timedelta(days=days)
