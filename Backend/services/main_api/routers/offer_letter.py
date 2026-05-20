from __future__ import annotations

from datetime import timezone

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.email_utils import send_email
from core.models import Application, Job, OfferWorkflow
from core.offer_letters import persist_signature_image, refresh_offer_documents, reset_offer_expiry
from core.workflow import ensure_offer_workflow, log_workflow_event, now_utc

router = APIRouter(tags=["offer-letter"])


class OfferGenerateRequest(BaseModel):
    application_id: int
    joining_date: str = ""
    compensation_text: str = ""
    employment_type: str = ""
    offered_compensation: str = ""
    contract_duration_or_notes: str = ""
    designation: str = ""
    department: str = ""
    company_details: str = ""
    work_location: str = ""
    work_mode: str = ""
    reporting_manager: str = ""
    reporting_team: str = ""
    hr_contact_details: str = ""
    onboarding_instructions: str = ""
    terms_and_conditions: str = ""
    offer_valid_until: str = ""
    actor_email: str = ""


class OfferRespondRequest(BaseModel):
    decision: str
    remarks: str = ""
    signature_data_url: str = ""
    signature_filename: str = "signature.png"


class OfferApprovalRequest(BaseModel):
    decision: str
    approver_email: str = ""
    reason: str = ""
    recommendation_score: float | None = None


def _get_offer_context(db: Session, application_id: int) -> tuple[Application, Job, OfferWorkflow]:
    application = db.query(Application).filter(Application.id == application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    offer = ensure_offer_workflow(db, application.id)
    return application, job, offer


def _is_expired(value) -> bool:
    if not value:
        return False
    if getattr(value, "tzinfo", None) is None:
        value = value.replace(tzinfo=timezone.utc)
    return value < now_utc()


def _serialize_offer_payload(application: Application, job: Job, offer: OfferWorkflow) -> dict:
    expired = _is_expired(offer.candidate_portal_expires_at)
    return {
        "application_id": application.id,
        "candidate_name": application.full_name,
        "candidate_email": application.email,
        "job_title": job.job_name,
        "job_location": job.location,
        "status": offer.status,
        "candidate_response": offer.candidate_response,
        "candidate_remarks": offer.candidate_remarks,
        "joining_date": offer.joining_date,
        "designation": offer.designation,
        "department": offer.department,
        "compensation_text": offer.compensation_text,
        "employment_type": offer.employment_type,
        "offered_compensation": offer.offered_compensation,
        "contract_duration_or_notes": offer.contract_duration_or_notes,
        "work_location": offer.work_location,
        "work_mode": offer.work_mode,
        "reporting_manager": offer.reporting_manager,
        "reporting_team": offer.reporting_team,
        "company_details": offer.company_details,
        "hr_contact_details": offer.hr_contact_details,
        "onboarding_instructions": offer.onboarding_instructions,
        "terms_and_conditions": offer.terms_and_conditions,
        "offer_valid_until": offer.offer_valid_until,
        "candidate_portal_expires_at": offer.candidate_portal_expires_at.isoformat() if offer.candidate_portal_expires_at else None,
        "offer_generated_at": offer.offer_generated_at.isoformat() if offer.offer_generated_at else None,
        "offer_sent_at": offer.offer_sent_at.isoformat() if offer.offer_sent_at else None,
        "candidate_response_at": offer.candidate_response_at.isoformat() if offer.candidate_response_at else None,
        "hr_final_approval_status": offer.hr_final_approval_status,
        "hr_final_approval_reason": offer.hr_final_approval_reason,
        "final_outcome": offer.final_outcome,
        "final_outcome_summary": offer.final_outcome_summary,
        "expired": expired,
        "preview_url": f"{settings.public_main_api_url}/offer-letter/{offer.token}/download?kind=unsigned",
        "signed_preview_url": f"{settings.public_main_api_url}/offer-letter/{offer.token}/download?kind=signed" if offer.signed_pdf_path else None,
        "download_url": f"{settings.public_main_api_url}/offer-letter/{offer.token}/download",
    }


@router.post("/offer-letter/generate", summary="Generate and send an offer letter")
def generate_offer_letter(body: OfferGenerateRequest, db: Session = Depends(get_db)):
    application, job, offer = _get_offer_context(db, body.application_id)
    if application.status not in {"offer_pending", "offer_sent", "offer_signed", "approval_pending", "hired", "on_hold", "onboarding_in_progress", "onboarding_completed"}:
        raise HTTPException(400, "Offer letter can only be generated after verification is approved.")

    for field in (
        "joining_date",
        "compensation_text",
        "employment_type",
        "offered_compensation",
        "contract_duration_or_notes",
        "designation",
        "department",
        "company_details",
        "work_location",
        "work_mode",
        "reporting_manager",
        "reporting_team",
        "hr_contact_details",
        "onboarding_instructions",
        "terms_and_conditions",
        "offer_valid_until",
    ):
        incoming = getattr(body, field)
        if incoming:
            setattr(offer, field, incoming)

    required_fields = {
        "joining_date": offer.joining_date,
        "employment_type": offer.employment_type,
        "offered_compensation": offer.offered_compensation or offer.compensation_text,
        "designation": offer.designation,
        "department": offer.department,
        "work_mode": offer.work_mode,
        "work_location": offer.work_location,
        "reporting_manager": offer.reporting_manager,
        "reporting_team": offer.reporting_team,
        "hr_contact_details": offer.hr_contact_details,
        "onboarding_instructions": offer.onboarding_instructions,
        "terms_and_conditions": offer.terms_and_conditions,
    }
    missing = [field for field, value in required_fields.items() if not str(value or "").strip()]
    if missing:
        raise HTTPException(400, f"Missing required offer fields: {', '.join(missing)}")
    employment_type = (offer.employment_type or "").strip().lower()
    if employment_type in {"contract", "consultant", "internship", "temporary"} and not str(offer.contract_duration_or_notes or "").strip():
        raise HTTPException(400, "Contract duration or notes are required for contract-like employment types.")

    reset_offer_expiry(offer)
    unsigned_path, _ = refresh_offer_documents(application, offer)
    offer.unsigned_pdf_path = unsigned_path
    offer.offer_generated_at = now_utc()
    offer.offer_sent_at = now_utc()
    offer.offer_email_to = application.email or ""
    offer.status = "offer_sent"
    application.status = "offer_sent"
    db.commit()

    portal_url = settings.public_frontend_path(f"/offer/{offer.token}")
    send_email(
        to=application.email,
        subject=f"Offer Letter — {job.job_name}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Your Offer Letter Is Ready</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{application.full_name}</strong>, your offer letter for
  <strong>{job.job_name}</strong> is ready for review.
</p>
<p style="margin:0 0 16px;font-size:15px;color:#555;line-height:1.7;">
  Use the secure temporary portal below to review the joining details, accept or reject the offer,
  and submit your digital signature. This access link expires automatically.
</p>
<table cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr><td style="background:#111;border-radius:8px;">
    <a href="{portal_url}" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:700;color:#fff;text-decoration:none;">Open Offer Portal</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Secure link: {portal_url}</p>
""",
        stage="offer_letter",
        application_id=application.id,
        meta={"offer_workflow_id": offer.id},
    )
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="offer_generated",
        summary="Offer letter generated and sent to candidate.",
        stage_key="offer_letter",
        actor_type="hr",
        actor_email=body.actor_email or job.posted_by,
        detail={"offer_workflow_id": offer.id},
    )
    return {
        **_serialize_offer_payload(application, job, offer),
        "pdf_url": f"{settings.public_main_api_url}/offer-letter/{offer.token}/download?kind=unsigned",
        "signing_url": portal_url,
    }


@router.get("/offer-letter/{token}", summary="Get offer portal payload by token")
def get_offer_letter(token: str, db: Session = Depends(get_db)):
    offer = db.query(OfferWorkflow).filter(OfferWorkflow.token == token).first()
    if not offer:
        raise HTTPException(404, "Offer workflow not found")
    application = db.query(Application).filter(Application.id == offer.application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if not offer.offer_link_opened_at:
        offer.offer_link_opened_at = now_utc()
        db.commit()
        log_workflow_event(
            db,
            application_id=application.id,
            event_type="offer_link_opened",
            summary="Candidate opened the offer portal.",
            stage_key="candidate_acceptance",
            actor_type="candidate",
            actor_email=application.email or "",
            detail={"offer_workflow_id": offer.id},
        )
    return _serialize_offer_payload(application, job, offer)


@router.post("/offer-letter/{token}/respond", summary="Submit candidate offer response")
def respond_to_offer(token: str, body: OfferRespondRequest, request: Request, db: Session = Depends(get_db)):
    offer = db.query(OfferWorkflow).filter(OfferWorkflow.token == token).first()
    if not offer:
        raise HTTPException(404, "Offer workflow not found")
    application = db.query(Application).filter(Application.id == offer.application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    if _is_expired(offer.candidate_portal_expires_at):
        raise HTTPException(400, "Offer portal has expired.")

    decision = body.decision.strip().lower()
    if decision not in {"accepted", "rejected"}:
        raise HTTPException(400, "Decision must be accepted or rejected.")
    if decision == "accepted" and not body.signature_data_url:
        raise HTTPException(400, "Signature is required to accept the offer.")

    offer.candidate_response = decision
    offer.candidate_remarks = body.remarks
    offer.candidate_response_at = now_utc()
    offer.candidate_ip = request.client.host if request.client else ""
    offer.candidate_user_agent = request.headers.get("user-agent", "")
    if decision == "accepted":
        offer.signature_type = "draw_or_upload"
        offer.signature_image_path = persist_signature_image(
            offer,
            data_url=body.signature_data_url,
            filename=body.signature_filename,
        )
        unsigned_path, signed_path = refresh_offer_documents(application, offer)
        offer.unsigned_pdf_path = unsigned_path
        offer.signed_pdf_path = signed_path or offer.signed_pdf_path
        offer.status = "offer_signed"
        application.status = "approval_pending"
    else:
        offer.status = "rejected"
        application.status = "rejected"
    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="candidate_offer_response",
        summary=f"Candidate {decision} the offer.",
        stage_key="candidate_acceptance",
        actor_type="candidate",
        actor_email=application.email or "",
        detail={"remarks": body.remarks},
    )
    return _serialize_offer_payload(application, job, offer)


@router.post("/offer-letter/{offer_id}/final-approval", summary="Submit HR final approval for a signed offer")
def final_approval(offer_id: int, body: OfferApprovalRequest, db: Session = Depends(get_db)):
    offer = db.query(OfferWorkflow).filter(OfferWorkflow.id == offer_id).first()
    if not offer:
        raise HTTPException(404, "Offer workflow not found")
    application = db.query(Application).filter(Application.id == offer.application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")

    decision = body.decision.strip().lower()
    if decision not in {"approved", "rejected", "on_hold"}:
        raise HTTPException(400, "Decision must be approved, rejected, or on_hold.")

    offer.hr_final_approval_status = decision
    offer.hr_final_approval_reason = body.reason
    offer.hr_final_approval_at = now_utc()
    offer.hr_final_approver = body.approver_email
    offer.final_recommendation_score = body.recommendation_score
    if decision == "approved":
        offer.final_outcome = "hired"
        offer.final_outcome_summary = body.reason or "Offer approved and candidate hired."
        offer.status = "approved"
        application.status = "hired"
    elif decision == "rejected":
        offer.final_outcome = "rejected"
        offer.final_outcome_summary = body.reason or "Offer rejected after final HR approval review."
        offer.status = "rejected"
        application.status = "rejected"
    else:
        offer.final_outcome = "on_hold"
        offer.final_outcome_summary = body.reason or "Offer kept on hold."
        offer.status = "on_hold"
        application.status = "on_hold"
    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="offer_final_approval",
        summary=f"Final approval recorded: {decision}.",
        stage_key="hr_final_approval",
        actor_type="hr",
        actor_email=body.approver_email,
        detail=body.model_dump(),
    )
    return _serialize_offer_payload(application, job, offer)


@router.get("/offer-letter/{token}/download", summary="Download offer PDF")
def download_offer_pdf(token: str, kind: str = "signed", db: Session = Depends(get_db)):
    offer = db.query(OfferWorkflow).filter(OfferWorkflow.token == token).first()
    if not offer:
        raise HTTPException(404, "Offer workflow not found")
    path = offer.signed_pdf_path if kind == "signed" and offer.signed_pdf_path else offer.unsigned_pdf_path
    if not path:
        raise HTTPException(404, "Offer PDF not available")
    return FileResponse(path=path, media_type="application/pdf", filename=path.split("\\")[-1].split("/")[-1])
