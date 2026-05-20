from __future__ import annotations

import json
from types import SimpleNamespace

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.email_utils import send_email
from core.models import Application, Job, LiveSession, OfferWorkflow, VerificationCase
from core.verification import create_verification_case, send_bgv_request_email
from core.workflow import (
    POST_INTERVIEW_STATUSES,
    build_workflow_payload,
    ensure_offer_workflow,
    log_workflow_event,
    now_utc,
)

router = APIRouter(tags=["workflow"])


class JoiningSetupRequest(BaseModel):
    joining_date: str = ""
    onboarding_instructions: str = ""
    work_mode: str = ""
    employment_type: str = ""
    reporting_manager: str = ""
    reporting_team: str = ""
    compensation_text: str = ""
    offered_compensation: str = ""
    contract_duration_or_notes: str = ""
    designation: str = ""
    department: str = ""
    company_details: str = ""
    work_location: str = ""
    hr_contact_details: str = ""
    terms_and_conditions: str = ""
    offer_valid_until: str = ""
    actor_email: str = ""


class FinalOutcomeRequest(BaseModel):
    outcome: str
    summary: str = ""
    recommendation_score: float | None = None
    actor_email: str = ""


class OnboardingRequest(BaseModel):
    onboarding_status: str
    notes: str = ""
    actor_email: str = ""


def _get_app_and_job(db: Session, app_id: int) -> tuple[Application, Job]:
    application = db.query(Application).filter(Application.id == app_id).first()
    if not application:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == application.job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return application, job


@router.get("/applications/{app_id}/workflow", summary="Get normalized workflow payload for a candidate")
def get_application_workflow(app_id: int, db: Session = Depends(get_db)):
    application, job = _get_app_and_job(db, app_id)
    return build_workflow_payload(db, application, job)


@router.patch("/applications/{app_id}/workflow/joining", summary="Save joining setup details")
def update_joining_setup(app_id: int, body: JoiningSetupRequest, db: Session = Depends(get_db)):
    application, job = _get_app_and_job(db, app_id)
    offer = ensure_offer_workflow(db, application.id)

    history = list(offer.joining_date_history_json and json.loads(offer.joining_date_history_json) or [])
    if body.joining_date and body.joining_date != offer.joining_date:
        history.append({
            "value": body.joining_date,
            "changed_at": now_utc().isoformat(),
            "changed_by": body.actor_email or "hr",
        })
        offer.joining_date_history_json = json.dumps(history)

    offer.joining_date = body.joining_date or offer.joining_date
    offer.onboarding_instructions = body.onboarding_instructions
    offer.work_mode = body.work_mode
    offer.employment_type = body.employment_type
    offer.reporting_manager = body.reporting_manager
    offer.reporting_team = body.reporting_team
    offer.compensation_text = body.compensation_text
    offer.offered_compensation = body.offered_compensation
    offer.contract_duration_or_notes = body.contract_duration_or_notes
    offer.designation = body.designation
    offer.department = body.department
    offer.company_details = body.company_details
    offer.work_location = body.work_location
    offer.hr_contact_details = body.hr_contact_details
    offer.terms_and_conditions = body.terms_and_conditions
    offer.offer_valid_until = body.offer_valid_until
    offer.status = "joining_pending"

    if application.status not in {"rejected", "bgv_pending", "bgv_review", "offer_pending", "offer_sent", "offer_signed", "approval_pending", "hired", "on_hold", "onboarding_in_progress", "onboarding_completed"}:
        application.status = "joining_pending"

    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="joining_setup_saved",
        summary=f"Joining setup updated for {job.job_name}.",
        stage_key="joining_setup",
        actor_type="hr",
        actor_email=body.actor_email,
        detail=body.model_dump(),
    )
    return build_workflow_payload(db, application, job)


@router.post("/applications/{app_id}/workflow/bgv/start", summary="Initiate background verification after joining setup")
def start_background_verification(app_id: int, db: Session = Depends(get_db)):
    application, job = _get_app_and_job(db, app_id)
    offer = ensure_offer_workflow(db, application.id)
    if not offer.joining_date:
        raise HTTPException(400, "Joining date must be set before starting background verification.")

    live_session = (
        db.query(LiveSession)
        .filter(LiveSession.application_id == application.id)
        .order_by(LiveSession.created_at.desc(), LiveSession.id.desc())
        .first()
    )
    if not live_session:
        live_session = SimpleNamespace(
            id=None,
            candidate_name=application.full_name,
            candidate_email=application.email,
            job_title=job.job_name,
            hr_email=job.posted_by,
            reference_face_b64=None,
        )

    existing_case = (
        db.query(VerificationCase)
        .filter(VerificationCase.application_id == application.id)
        .order_by(VerificationCase.created_at.desc(), VerificationCase.id.desc())
        .first()
    )
    case = existing_case or create_verification_case(db, application, live_session)
    application.status = "bgv_pending"
    offer.status = "bgv_pending"
    offer.bgv_initiated_at = now_utc()
    offer.bgv_started_by = job.posted_by or ""
    db.commit()
    send_bgv_request_email(case)
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="bgv_started",
        summary="Background verification initiated.",
        stage_key="background_verification",
        actor_type="hr",
        actor_email=job.posted_by or "",
        detail={"verification_case_id": case.id},
    )
    return build_workflow_payload(db, application, job)


@router.patch("/applications/{app_id}/workflow/final-outcome", summary="Update final hiring outcome")
def update_final_outcome(app_id: int, body: FinalOutcomeRequest, db: Session = Depends(get_db)):
    application, job = _get_app_and_job(db, app_id)
    offer = ensure_offer_workflow(db, application.id)
    normalized = body.outcome.strip().lower()
    if normalized not in {"hired", "rejected", "on_hold"}:
        raise HTTPException(400, "Outcome must be hired, rejected, or on_hold.")

    offer.final_outcome = normalized
    offer.final_outcome_summary = body.summary
    offer.final_recommendation_score = body.recommendation_score
    application.status = normalized
    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="final_outcome_updated",
        summary=f"Final outcome set to {normalized}.",
        stage_key="final_hiring_outcome",
        actor_type="hr",
        actor_email=body.actor_email,
        detail=body.model_dump(),
    )
    return build_workflow_payload(db, application, job)


@router.patch("/applications/{app_id}/workflow/onboarding", summary="Update onboarding status")
def update_onboarding(app_id: int, body: OnboardingRequest, db: Session = Depends(get_db)):
    application, job = _get_app_and_job(db, app_id)
    offer = ensure_offer_workflow(db, application.id)
    normalized = body.onboarding_status.strip().lower()
    if normalized not in {"pending", "in_progress", "completed"}:
        raise HTTPException(400, "Onboarding status must be pending, in_progress, or completed.")

    offer.onboarding_status = normalized
    offer.onboarding_notes = body.notes
    if normalized == "in_progress":
        offer.onboarding_started_at = offer.onboarding_started_at or now_utc()
        application.status = "onboarding_in_progress"
    elif normalized == "completed":
        offer.onboarding_completed_at = now_utc()
        application.status = "onboarding_completed"
    else:
        if application.status in POST_INTERVIEW_STATUSES:
            application.status = "hired" if offer.final_outcome == "hired" else application.status
    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="onboarding_updated",
        summary=f"Onboarding status updated to {normalized}.",
        stage_key="employee_onboarding",
        actor_type="hr",
        actor_email=body.actor_email,
        detail=body.model_dump(),
    )
    return build_workflow_payload(db, application, job)
