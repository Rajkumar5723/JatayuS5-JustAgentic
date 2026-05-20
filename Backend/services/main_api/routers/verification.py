from __future__ import annotations

import base64
import json

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session, object_session

from core.database import get_db
from core.document_pipeline import document_definition, document_storage
from core.models import Application, VerificationCase, VerificationDocument
from core.verification import review_verification_case, submit_verification_case

router = APIRouter(tags=["verification"])


class VerificationSubmitRequest(BaseModel):
    full_name: str = ""
    address: str = ""
    city: str = ""
    state: str = ""
    pincode: str = ""
    pan_number: str = ""
    aadhaar_number: str = ""
    documents: dict = {}


class VerificationReviewRequest(BaseModel):
    reviewer_email: str = ""
    decision: str
    reason: str = ""


def _serialize_case(case: VerificationCase) -> dict:
    documents = json.loads(case.documents_json or "{}")
    ocr = json.loads(case.ocr_json or "{}")
    verification_docs = _verification_documents(case)
    return {
        "id": case.id,
        "token": case.token,
        "application_id": case.application_id,
        "live_session_id": case.live_session_id,
        "candidate_name": case.candidate_name,
        "candidate_email": case.candidate_email,
        "job_title": case.job_title,
        "hr_email": case.hr_email,
        "status": case.status,
        "typed_full_name": case.typed_full_name,
        "typed_address": case.typed_address,
        "typed_city": case.typed_city,
        "typed_state": case.typed_state,
        "typed_pincode": case.typed_pincode,
        "typed_pan": case.typed_pan,
        "typed_aadhaar": case.typed_aadhaar,
        "documents": documents,
        "ocr": ocr,
        "document_items": verification_docs,
        "face": json.loads(case.face_json or "{}"),
        "mismatches": json.loads(case.mismatch_json or "[]"),
        "review_summary": case.review_summary,
        "manual_decision": case.manual_decision,
        "review_reason": case.review_reason,
        "reviewer_email": case.reviewer_email,
        "created_at": str(case.created_at),
        "submitted_at": str(case.submitted_at) if case.submitted_at else None,
        "reviewed_at": str(case.reviewed_at) if case.reviewed_at else None,
    }


def _verification_documents(case: VerificationCase) -> list[dict]:
    db = object_session(case)
    if db is None:
        return []
    storage = document_storage(db)
    rows = (
        db.query(VerificationDocument)
        .filter(VerificationDocument.verification_case_id == case.id)
        .order_by(VerificationDocument.uploaded_at.asc(), VerificationDocument.id.asc())
        .all()
    )
    return [
        {
            "id": row.id,
            "document_type": row.document_type,
            "required": bool(row.required),
            "category": row.category,
            "filename": row.original_filename,
            "mime_type": row.mime_type,
            "storage_key": row.s3_key,
            "storage_url": storage.generate_presigned_url(row.s3_key),
            "download_url": storage.generate_presigned_url(row.s3_key),
            "ocr_status": row.ocr_status,
            "ocr_fields": json.loads(row.ocr_json or "{}").get("fields", {}),
            "verification_status": row.verification_status,
            "uploaded_at": str(row.uploaded_at) if row.uploaded_at else None,
        }
        for row in rows
    ]


@router.get("/verification/{token}", summary="Get a verification case by token")
def get_case(token: str, db: Session = Depends(get_db)):
    case = db.query(VerificationCase).filter(VerificationCase.token == token).first()
    if not case:
        raise HTTPException(404, "Verification case not found")
    return _serialize_case(case)


@router.get("/verification/application/{app_id}", summary="Get the latest verification case for an application")
def get_case_for_application(app_id: int, db: Session = Depends(get_db)):
    """Returns null when BGV has not started yet (avoids noisy 404s in HR dashboard)."""
    case = (
        db.query(VerificationCase)
        .filter(VerificationCase.application_id == app_id)
        .order_by(VerificationCase.created_at.desc(), VerificationCase.id.desc())
        .first()
    )
    if not case:
        return None
    return _serialize_case(case)


@router.post("/verification/{token}/submit", summary="Submit candidate verification documents")
async def submit_case(
    token: str,
    full_name: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    state: str = Form(""),
    pincode: str = Form(""),
    pan_number: str = Form(""),
    aadhaar_number: str = Form(""),
    selfie_file: UploadFile | None = File(default=None),
    aadhaar_file: UploadFile | None = File(default=None),
    pan_file: UploadFile | None = File(default=None),
    ug_marksheet_file: UploadFile | None = File(default=None),
    pg_marksheet_file: UploadFile | None = File(default=None),
    marksheet_10_file: UploadFile | None = File(default=None),
    marksheet_12_file: UploadFile | None = File(default=None),
    passport_file: UploadFile | None = File(default=None),
    db: Session = Depends(get_db),
):
    case = db.query(VerificationCase).filter(VerificationCase.token == token).first()
    if not case:
        raise HTTPException(404, "Verification case not found")
    application = db.query(Application).filter(Application.id == case.application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")

    uploads = {
        "selfie": selfie_file,
        "aadhaar": aadhaar_file,
        "pan": pan_file,
        "ug_marksheet": ug_marksheet_file,
        "pg_marksheet": pg_marksheet_file,
        "marksheet_10": marksheet_10_file,
        "marksheet_12": marksheet_12_file,
        "passport": passport_file,
    }

    documents = {}
    for doc_key, upload in uploads.items():
        if upload is None:
            continue
        payload = await upload.read()
        if not payload:
            continue
        definition = document_definition(doc_key)
        documents[doc_key] = {
            "filename": upload.filename or f"{doc_key}.bin",
            "mime_type": upload.content_type or "application/octet-stream",
            "content": (
                f"data:{upload.content_type or 'application/octet-stream'};base64,"
                f"{base64.b64encode(payload).decode('ascii')}"
            ),
            "required": bool(definition["required"]),
            "category": definition["category"],
        }

    payload = VerificationSubmitRequest(
        full_name=full_name,
        address=address,
        city=city,
        state=state,
        pincode=pincode,
        pan_number=pan_number,
        aadhaar_number=aadhaar_number,
        documents=documents,
    ).model_dump()
    case = await submit_verification_case(db, case, application, payload)
    db.refresh(case)
    return _serialize_case(case)


@router.post("/verification/{case_id}/review", summary="Submit the final human verification decision")
def review_case(case_id: int, body: VerificationReviewRequest, db: Session = Depends(get_db)):
    case = db.query(VerificationCase).filter(VerificationCase.id == case_id).first()
    if not case:
        raise HTTPException(404, "Verification case not found")
    application = db.query(Application).filter(Application.id == case.application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")

    case = review_verification_case(
        db,
        case,
        application,
        reviewer_email=body.reviewer_email,
        decision=body.decision,
        reason=body.reason,
    )
    db.refresh(case)
    return _serialize_case(case)
