from __future__ import annotations

import base64
import json
import re
import uuid
from datetime import datetime, timezone
from typing import Any

from core.config import settings
from core.document_pipeline import (
    document_definition,
    extract_document_text,
    json_value,
    store_document_bytes,
)
from core.email_utils import send_email
from core.models import Application, VerificationCase, VerificationDocument
from core.proctoring import image_similarity
from core.workflow import ensure_offer_workflow, log_workflow_event


DOC_KEYS = (
    "selfie",
    "aadhaar",
    "pan",
    "ug_marksheet",
    "pg_marksheet",
    "marksheet_10",
    "marksheet_12",
    "passport",
)
FACE_DOC_KEYS = {"aadhaar", "pan", "passport"}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _normalise(value: str | None) -> str:
    return re.sub(r"[^a-z0-9]", "", (value or "").lower())


def _data_url_to_bytes(value: str | None) -> bytes:
    if not value:
        return b""
    data = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    return base64.b64decode(data)


def _data_url_from_bytes(mime_type: str, payload: bytes) -> str:
    encoded = base64.b64encode(payload).decode("ascii")
    return f"data:{mime_type};base64,{encoded}"


def _document_bytes(doc: dict[str, Any]) -> bytes:
    payload = doc.get("payload")
    if isinstance(payload, bytes):
        return payload
    if isinstance(payload, bytearray):
        return bytes(payload)
    return _data_url_to_bytes(doc.get("content") or "")


def _document_data_url(doc: dict[str, Any], mime_type: str) -> str:
    content = doc.get("content")
    if isinstance(content, str) and content:
        return content
    payload = _document_bytes(doc)
    return _data_url_from_bytes(mime_type, payload) if payload else ""


def _combined_ocr_text(documents: list[VerificationDocument]) -> str:
    return "\n".join((doc.ocr_text or "").strip() for doc in documents if (doc.ocr_text or "").strip())


def _field_match(mismatches: list[str], key: str, typed_value: str, extracted_value: str) -> None:
    if not typed_value:
        return
    if extracted_value:
        if _normalise(typed_value) != _normalise(extracted_value):
            mismatches.append(f"{key}_mismatch")
    else:
        mismatches.append(f"{key}_ocr_missing")


def _review_summary(mismatches: list[str], face_similarity: float | None) -> str:
    if not mismatches and (face_similarity is None or face_similarity >= 0.55):
        return "Documents are consistent with the submitted details and face continuity looks acceptable."
    parts = []
    if mismatches:
        parts.append("Mismatches: " + "; ".join(mismatches))
    if face_similarity is not None:
        parts.append(f"Reference face similarity: {face_similarity:.2f}")
    return " | ".join(parts)


def create_verification_case(db, application: Application, live_session) -> VerificationCase:
    existing = (
        db.query(VerificationCase)
        .filter(VerificationCase.application_id == application.id)
        .order_by(VerificationCase.created_at.desc(), VerificationCase.id.desc())
        .first()
    )
    if existing:
        return existing

    case = VerificationCase(
        token=uuid.uuid4().hex[:24],
        application_id=application.id,
        live_session_id=getattr(live_session, "id", None),
        candidate_name=application.full_name or live_session.candidate_name,
        candidate_email=application.email or live_session.candidate_email,
        job_title=live_session.job_title,
        hr_email=getattr(live_session, "hr_email", "") or "",
        reference_face_b64=getattr(live_session, "reference_face_b64", None),
        typed_full_name=application.full_name or live_session.candidate_name,
    )
    db.add(case)
    db.commit()
    db.refresh(case)
    return case


def send_bgv_request_email(case: VerificationCase) -> bool:
    verify_url = settings.public_frontend_path(f"/verify/{case.token}")
    return send_email(
        to=case.candidate_email,
        subject=f"Background Verification Required - {case.job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Background Verification Required</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{case.candidate_name}</strong>, you have cleared the live HR round for
  <strong>{case.job_title}</strong>. Please complete the final background verification step.
</p>
<p style="margin:0 0 16px;font-size:15px;color:#555;line-height:1.7;">
  Required documents: Selfie, Aadhaar, UG marksheet, 10th marksheet, and 12th marksheet.
  PAN, PG marksheet, and passport are optional.
</p>
<table cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr><td style="background:#111;border-radius:8px;">
    <a href="{verify_url}" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:700;color:#fff;text-decoration:none;">Complete Verification</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Or copy this link: {verify_url}</p>
""",
        stage="bgv_request",
        application_id=case.application_id,
        verification_case_id=case.id,
    )


def send_bgv_ready_email(case: VerificationCase) -> bool:
    if not case.hr_email:
        return False
    return send_email(
        to=case.hr_email,
        subject=f"Verification Ready for Review - {case.candidate_name}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Verification Submitted</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  <strong>{case.candidate_name}</strong> has submitted their background verification documents for
  <strong>{case.job_title}</strong>.
</p>
<p style="margin:0;font-size:15px;color:#555;line-height:1.7;">
  Open the HR dashboard to review grouped documents, OCR matches, face checks, and the final recommendation.
</p>
""",
        stage="bgv_review_ready",
        application_id=case.application_id,
        verification_case_id=case.id,
    )


async def submit_verification_case(db, case: VerificationCase, application: Application, payload: dict[str, Any]) -> VerificationCase:
    uploaded_docs = payload.get("documents") or {}
    selfie_doc = uploaded_docs.get("selfie") or {}
    selfie_mime = selfie_doc.get("mime_type") or "image/jpeg"
    selfie_bytes = _document_bytes(selfie_doc)
    selfie_content = _document_data_url(selfie_doc, selfie_mime) if selfie_bytes else ""

    existing_docs = (
        db.query(VerificationDocument)
        .filter(VerificationDocument.verification_case_id == case.id)
        .all()
    )
    existing_by_type = {row.document_type: row for row in existing_docs}

    documents_summary: dict[str, str] = {}
    ocr_summary: dict[str, Any] = {}
    stored_documents: list[VerificationDocument] = []
    mismatches: list[str] = []

    for doc_key in DOC_KEYS:
        definition = document_definition(doc_key)
        doc = uploaded_docs.get(doc_key)
        if not doc:
            existing_row = existing_by_type.get(doc_key)
            if existing_row is not None:
                documents_summary[doc_key] = existing_row.s3_key
                parsed_ocr = json.loads(existing_row.ocr_json or "{}")
                ocr_summary[doc_key] = {
                    "s3_key": existing_row.s3_key,
                    "filename": existing_row.original_filename,
                    "mime_type": existing_row.mime_type,
                    "ocr_status": existing_row.ocr_status,
                    "ocr_method": parsed_ocr.get("ocr_method", ""),
                    "fields": parsed_ocr.get("fields", {}),
                    "text": (existing_row.ocr_text or "")[:5000],
                }
                stored_documents.append(existing_row)
                continue
            if definition.get("required"):
                mismatches.append(f"missing_{doc_key}")
            continue

        existing_row = existing_by_type.get(doc_key)
        if existing_row is not None:
            db.delete(existing_row)
            db.flush()

        filename = doc.get("filename") or f"{doc_key}.bin"
        mime_type = doc.get("mime_type") or "application/octet-stream"
        file_bytes = _document_bytes(doc)
        if not file_bytes:
            continue
        storage_key, file_size = await store_document_bytes(
            db,
            session_token=case.token,
            document_type=doc_key,
            filename=filename,
            mime_type=mime_type,
            payload=file_bytes,
        )
        # Keep candidate submission responsive; full OCR can be reviewed/re-run later.
        ocr_result = extract_document_text(filename, mime_type, file_bytes, allow_ocr=False)
        verification_document = VerificationDocument(
            verification_case_id=case.id,
            document_type=doc_key,
            category=definition["category"],
            required=bool(definition["required"]),
            s3_key=storage_key,
            original_filename=filename,
            mime_type=mime_type,
            file_size_bytes=file_size,
            ocr_text=ocr_result["text"],
            ocr_json=json_value(
                {
                    "fields": ocr_result["fields"],
                    "ocr_method": ocr_result["ocr_method"],
                }
            ),
            ocr_status=ocr_result["ocr_status"],
            verification_status="pending",
        )
        db.add(verification_document)
        db.flush()
        documents_summary[doc_key] = storage_key
        ocr_summary[doc_key] = {
            "s3_key": storage_key,
            "filename": filename,
            "mime_type": mime_type,
            "ocr_status": ocr_result["ocr_status"],
            "ocr_method": ocr_result["ocr_method"],
            "fields": ocr_result["fields"],
            "text": ocr_result["text"][:5000],
        }
        stored_documents.append(verification_document)

    typed_full_name = payload.get("full_name") or application.full_name or case.candidate_name
    typed_address = payload.get("address") or application.location or ""
    typed_city = payload.get("city") or ""
    typed_state = payload.get("state") or ""
    typed_pincode = re.sub(r"\D+", "", payload.get("pincode") or "")
    typed_pan = (payload.get("pan_number") or "").upper()
    typed_aadhaar = re.sub(r"\s+", "", payload.get("aadhaar_number") or "")

    case.typed_full_name = typed_full_name
    case.typed_address = typed_address
    case.typed_city = typed_city
    case.typed_state = typed_state
    case.typed_pincode = typed_pincode
    case.typed_pan = typed_pan
    case.typed_aadhaar = typed_aadhaar
    case.payload_json = json.dumps(
        {
            "full_name": typed_full_name,
            "address": typed_address,
            "city": typed_city,
            "state": typed_state,
            "pincode": typed_pincode,
            "pan_number": typed_pan,
            "aadhaar_number": typed_aadhaar,
        }
    )
    case.documents_json = json.dumps(documents_summary)
    case.ocr_json = json.dumps(ocr_summary)

    extracted_fields: dict[str, Any] = {}
    for item in stored_documents:
        try:
            data = json.loads(item.ocr_json or "{}")
        except Exception:
            data = {}
        fields = data.get("fields") or {}
        for field_name, field_value in fields.items():
            if field_value and not extracted_fields.get(field_name):
                extracted_fields[field_name] = field_value

    combined_text = _combined_ocr_text(stored_documents)
    _field_match(mismatches, "pan", typed_pan, str(extracted_fields.get("pan") or ""))
    _field_match(mismatches, "aadhaar", typed_aadhaar, str(extracted_fields.get("aadhaar") or ""))
    _field_match(mismatches, "pincode", typed_pincode, str(extracted_fields.get("pincode") or ""))

    if typed_full_name and combined_text and _normalise(typed_full_name) not in _normalise(combined_text):
        mismatches.append("name_not_found_in_documents")
    if typed_address and combined_text and _normalise(typed_address) not in _normalise(combined_text):
        mismatches.append("address_not_found_in_documents")
    if typed_city and extracted_fields.get("city") and _normalise(typed_city) != _normalise(extracted_fields.get("city")):
        mismatches.append("city_mismatch")
    if typed_state and extracted_fields.get("state") and _normalise(typed_state) != _normalise(extracted_fields.get("state")):
        mismatches.append("state_mismatch")

    previous_face = json.loads(case.face_json or "{}") if case.face_json else {}
    reference_similarity = image_similarity(case.reference_face_b64, selfie_content) if selfie_content else previous_face.get("reference_similarity")
    document_face_similarity: dict[str, Any] = dict(previous_face.get("document_face_similarity") or {})
    if selfie_bytes:
        document_face_similarity = {}
        for doc_key in FACE_DOC_KEYS:
            doc = uploaded_docs.get(doc_key) or {}
            mime_type = str(doc.get("mime_type") or "")
            content = _document_data_url(doc, mime_type)
            if content and mime_type.startswith("image/"):
                document_face_similarity[doc_key] = image_similarity(
                    selfie_content,
                    content,
                )
    case.face_json = json.dumps(
        {
            "reference_similarity": reference_similarity,
            "document_face_similarity": document_face_similarity,
        }
    )
    if reference_similarity is not None and reference_similarity < 0.55:
        mismatches.append("reference_face_low_similarity")

    case.mismatch_json = json.dumps(sorted(set(mismatches)))
    case.review_summary = _review_summary(sorted(set(mismatches)), reference_similarity)
    case.status = "submitted"
    case.submitted_at = _now()
    application.status = "bgv_review"

    db.commit()
    send_bgv_ready_email(case)
    return case


def review_verification_case(
    db,
    case: VerificationCase,
    application: Application,
    *,
    reviewer_email: str,
    decision: str,
    reason: str,
) -> VerificationCase:
    decision = decision.lower().strip()
    case.reviewer_email = reviewer_email
    case.manual_decision = decision
    case.review_reason = reason
    case.reviewed_at = _now()

    docs = (
        db.query(VerificationDocument)
        .filter(VerificationDocument.verification_case_id == case.id)
        .all()
    )

    if decision == "accept":
        case.status = "accepted"
        application.status = "offer_pending"
        for doc in docs:
            doc.verification_status = "verified"
        offer = ensure_offer_workflow(db, application.id)
        offer.status = "offer_pending"
        send_email(
            to=case.candidate_email,
            subject=f"Verification Approved - Offer Preparation | {case.job_title}",
            body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Verification Approved</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{case.candidate_name}</strong>, your background verification for
  <strong>{case.job_title}</strong> is complete.
</p>
<p style="margin:0;font-size:15px;color:#555;line-height:1.7;">Our HR team is preparing your offer details and will contact you with the next steps shortly.</p>
""",
            stage="final_acceptance",
            application_id=case.application_id,
            verification_case_id=case.id,
        )
    elif decision == "reject":
        case.status = "rejected"
        application.status = "rejected"
        for doc in docs:
            doc.verification_status = "rejected"
        send_email(
            to=case.candidate_email,
            subject=f"Application Update - {case.job_title}",
            body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Application Update</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{case.candidate_name}</strong>, after the final verification review we will not be moving
  forward with your application for <strong>{case.job_title}</strong>.
</p>
<p style="margin:0;font-size:15px;color:#555;line-height:1.7;">Thank you for your time and effort throughout the process.</p>
""",
            stage="final_rejection",
            application_id=case.application_id,
            verification_case_id=case.id,
        )
    else:
        case.status = "hold"
        application.status = "bgv_review"
        for doc in docs:
            doc.verification_status = "pending"

    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="verification_reviewed",
        summary=f"Verification review recorded as {decision}.",
        stage_key="background_verification",
        actor_type="hr",
        actor_email=reviewer_email,
        detail={"decision": decision, "reason": reason, "verification_case_id": case.id},
    )
    return case
