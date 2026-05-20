"""
core/models.py
==============
All SQLAlchemy ORM models for the Hiresy platform.
Single source of truth — no more per-service model redeclarations.
"""
from __future__ import annotations
from datetime import datetime, timezone
from sqlalchemy import (
    Boolean, Column, DateTime, Float, Integer, String, Text
)
from sqlalchemy.sql import func
from core.database import Base


def _now():
    return datetime.now(timezone.utc)


# ── Users ─────────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String, nullable=False)
    email    = Column(String, unique=True, index=True, nullable=False)
    password = Column(String, nullable=False)


# ── Jobs ──────────────────────────────────────────────────────
class Job(Base):
    __tablename__ = "jobs"

    id                 = Column(Integer, primary_key=True, index=True)
    posted_by          = Column(String, index=True, nullable=False)
    job_name           = Column(String, nullable=False)
    description        = Column(Text, nullable=False)
    salary_start       = Column(String, nullable=True)
    salary_end         = Column(String, nullable=True)
    show_salary        = Column(String, default="false")
    work_style         = Column(String, nullable=True)
    location           = Column(String, nullable=True)   # Added for On-Site location
    job_type           = Column(String, nullable=True)
    skills             = Column(String, nullable=True)
    exp_min            = Column(String, nullable=True)
    exp_max            = Column(String, nullable=True)
    department         = Column(String, nullable=True)
    openings           = Column(Integer, nullable=True)
    deadline           = Column(String, nullable=True)
    application_fields = Column(Text, nullable=True)
    difficulty         = Column(String, nullable=True)
    rounds             = Column(Text, nullable=True)
    platforms          = Column(String, nullable=True)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


# ── Applications ──────────────────────────────────────────────
class Application(Base):
    __tablename__ = "applications"

    id           = Column(Integer, primary_key=True, index=True)
    job_id       = Column(Integer, nullable=False, index=True)
    submitted_at = Column(DateTime, default=_now)

    # Personal
    full_name    = Column(String, nullable=True)
    email        = Column(String, nullable=True)
    phone        = Column(String, nullable=True)
    alt_phone    = Column(String, nullable=True)
    location     = Column(String, nullable=True)

    # Links
    resume_url    = Column(String, nullable=True)
    linkedin_url  = Column(String, nullable=True)
    github_url    = Column(String, nullable=True)
    leetcode_url  = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)

    # Education
    degree_type    = Column(String, nullable=True)
    field_of_study = Column(String, nullable=True)
    institution    = Column(String, nullable=True)

    # Experience
    years_exp     = Column(String, nullable=True)
    current_title = Column(String, nullable=True)
    company_name  = Column(String, nullable=True)
    current_lpa   = Column(String, nullable=True)
    notice_period = Column(String, nullable=True)

    # Skills
    technical_skills = Column(String, nullable=True)
    soft_skills      = Column(String, nullable=True)

    # Extra
    cover_letter = Column(String, nullable=True)
    extra_fields = Column(Text, nullable=True)   # JSON blob for custom fields

    # Pipeline status
    status = Column(String, default="pending")   # pending|selected|rejected|round_2|round_3

    # AI Evaluation (Stage 0)
    eval_score          = Column(String,  nullable=True)
    eval_recommendation = Column(String,  nullable=True)
    eval_summary        = Column(String,  nullable=True)
    eval_data           = Column(Text,    nullable=True)   # full JSON from eval service


# ── Live HR Sessions ──────────────────────────────────────────
class LiveSession(Base):
    __tablename__ = "live_hr_sessions"

    id              = Column(Integer, primary_key=True)
    token           = Column(String, unique=True, index=True, nullable=False)
    meet_code       = Column(String, nullable=False)
    application_id  = Column(Integer, index=True)
    candidate_name  = Column(String, nullable=False)
    candidate_email = Column(String, nullable=False)
    job_title       = Column(String, nullable=False)
    job_skills      = Column(String, default="")
    github_url      = Column(String, default="")
    github_data     = Column(Text,   default="{}")
    eval_summary    = Column(Text,   default="")
    scheduled_time  = Column(String, default="")
    transcript      = Column(Text,   default="")
    suggestions     = Column(Text,   default="[]")
    candidate_score = Column(Text,   default="{}")
    status          = Column(String, default="pending")   # pending|active|ended
    outcome         = Column(String, default="")          # pass|fail
    interview_type  = Column(String, default="copilot")   # copilot|hr_interview
    hr_email        = Column(String, default="")
    ai_score_json   = Column(Text,   default="{}")
    ai_reason       = Column(Text,   default="")
    ai_flags_json   = Column(Text,   default="[]")
    manual_score_json = Column(Text, default="{}")
    manual_reason   = Column(Text,   default="")
    final_summary   = Column(Text,   default="")
    reference_face_b64 = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=_now)
    started_at      = Column(DateTime, nullable=True)


# ── Shortlisting Tests ────────────────────────────────────────
class TestSession(Base):
    __tablename__ = "shortlist_tests"

    id              = Column(Integer, primary_key=True, index=True)
    token           = Column(String, unique=True, index=True, nullable=False)
    application_id  = Column(Integer, index=True)
    job_id          = Column(Integer, index=True)
    candidate_name  = Column(String, nullable=False)
    candidate_email = Column(String, nullable=False)
    job_title       = Column(String, nullable=False)
    job_skills      = Column(String, nullable=True)
    assessment_kind = Column(String, default="mcq")
    questions_json  = Column(Text, nullable=False)
    duration_mins   = Column(Integer, default=20)
    total_questions = Column(Integer, default=10)
    answers_json    = Column(Text, nullable=True)
    score           = Column(Float, nullable=True)
    score_pct       = Column(Float, nullable=True)
    passed          = Column(Boolean, nullable=True)
    pass_score      = Column(Integer, default=60)
    started_at      = Column(DateTime, nullable=True)
    submitted_at    = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=_now)
    email_sent      = Column(Boolean, default=False)
    status          = Column(String, default="pending")   # pending|started|submitted
    proctoring_risk = Column(String, nullable=True)
    risk_score      = Column(Float, nullable=True)
    block_reason    = Column(String, nullable=True)
    face_continuity_score = Column(Float, nullable=True)
    verification_face_b64 = Column(Text, nullable=True)
    proctoring_json = Column(Text, nullable=True)


# ── Coding / Multi-Round Tests ────────────────────────────────
class CodingSession(Base):
    __tablename__ = "coding_rounds"

    id               = Column(Integer, primary_key=True, index=True)
    token            = Column(String, unique=True, index=True, nullable=False)
    application_id   = Column(Integer, index=True)
    job_id           = Column(Integer, index=True)
    candidate_name   = Column(String, nullable=False)
    candidate_email  = Column(String, nullable=False)
    job_title        = Column(String, nullable=False)
    job_skills       = Column(String, nullable=True)
    resume_text      = Column(Text,   nullable=True)   # for skill-authenticity proctoring
    round_type       = Column(String, default="coding")  # coding|oop|database|api
    questions_json   = Column(Text, nullable=True)     # MCQ questions (new rounds)
    problems_json    = Column(Text, nullable=True)     # kept for legacy coding sessions
    answers_json     = Column(Text, nullable=True)
    duration_mins    = Column(Integer, default=60)
    total_questions  = Column(Integer, default=15)
    pass_score       = Column(Integer, default=60)
    score            = Column(Float, nullable=True)
    score_pct        = Column(Float, nullable=True)
    passed           = Column(Boolean, nullable=True)
    submissions_json = Column(Text, nullable=True)     # legacy coding submissions
    started_at       = Column(DateTime, nullable=True)
    submitted_at     = Column(DateTime, nullable=True)
    created_at       = Column(DateTime, default=_now)
    email_sent       = Column(Boolean, default=False)
    status           = Column(String, default="pending")   # pending|started|submitted
    # ── AI Proctoring ──
    proctoring_risk    = Column(String, nullable=True)    # low|medium|high|unknown
    risk_score         = Column(Float, nullable=True)
    block_reason       = Column(String, nullable=True)
    face_continuity_score = Column(Float, nullable=True)
    verification_face_b64 = Column(Text, nullable=True)
    authenticity_score = Column(Integer, nullable=True)   # 0-100
    proctoring_json    = Column(Text, nullable=True)      # full proctoring report JSON


# ── LinkedIn Accounts ─────────────────────────────────────────
class LinkedInAccount(Base):
    __tablename__ = "linkedin_accounts"

    hr_email     = Column(String, primary_key=True, index=True)
    person_urn   = Column(String, nullable=True)
    access_token = Column(String, nullable=False)
    expires_at   = Column(String, nullable=True)


class ProctoringEvidence(Base):
    __tablename__ = "proctoring_evidence"

    id                = Column(Integer, primary_key=True, index=True)
    application_id    = Column(Integer, index=True, nullable=True)
    test_session_id   = Column(Integer, index=True, nullable=True)
    coding_session_id = Column(Integer, index=True, nullable=True)
    live_session_id   = Column(Integer, index=True, nullable=True)
    session_token     = Column(String, index=True, nullable=False)
    round_name        = Column(String, nullable=True)
    event_type        = Column(String, nullable=False)
    severity          = Column(String, default="info")
    risk_delta        = Column(Float, default=0)
    evidence_json     = Column(Text, default="{}")
    created_at        = Column(DateTime, default=_now)


class VerificationCase(Base):
    __tablename__ = "verification_cases"

    id                = Column(Integer, primary_key=True, index=True)
    token             = Column(String, unique=True, index=True, nullable=False)
    application_id    = Column(Integer, index=True, nullable=False)
    live_session_id   = Column(Integer, index=True, nullable=True)
    candidate_name    = Column(String, nullable=False)
    candidate_email   = Column(String, nullable=False)
    job_title         = Column(String, nullable=False)
    hr_email          = Column(String, default="")
    status            = Column(String, default="pending_candidate")
    reference_face_b64 = Column(Text, nullable=True)
    typed_full_name   = Column(String, nullable=True)
    typed_address     = Column(Text, nullable=True)
    typed_city        = Column(String, nullable=True)
    typed_state       = Column(String, nullable=True)
    typed_pincode     = Column(String, nullable=True)
    typed_pan         = Column(String, nullable=True)
    typed_aadhaar     = Column(String, nullable=True)
    payload_json      = Column(Text, default="{}")
    documents_json    = Column(Text, default="{}")
    ocr_json          = Column(Text, default="{}")
    face_json         = Column(Text, default="{}")
    mismatch_json     = Column(Text, default="[]")
    review_summary    = Column(Text, default="")
    manual_decision   = Column(String, default="")
    review_reason     = Column(Text, default="")
    reviewer_email    = Column(String, default="")
    created_at        = Column(DateTime, default=_now)
    submitted_at      = Column(DateTime, nullable=True)
    reviewed_at       = Column(DateTime, nullable=True)


class EmailDeliveryLog(Base):
    __tablename__ = "email_delivery_logs"

    id                   = Column(Integer, primary_key=True, index=True)
    to_email             = Column(String, nullable=False)
    subject              = Column(String, nullable=False)
    stage                = Column(String, nullable=True)
    status               = Column(String, nullable=False)
    provider             = Column(String, default="smtp_ssl_gmail")
    error_message        = Column(Text, nullable=True)
    application_id       = Column(Integer, index=True, nullable=True)
    test_session_id      = Column(Integer, index=True, nullable=True)
    coding_session_id    = Column(Integer, index=True, nullable=True)
    live_session_id      = Column(Integer, index=True, nullable=True)
    verification_case_id = Column(Integer, index=True, nullable=True)
    meta_json            = Column(Text, default="{}")
    created_at           = Column(DateTime, default=_now)


# ── Enhanced Proctoring Evidence System ───────────────────────
class EvidenceFile(Base):
    __tablename__ = "evidence_files"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    evidence_type     = Column(String, nullable=False)  # photo, audio, video
    s3_key            = Column(String, nullable=False, unique=True)
    file_size_bytes   = Column(Integer, nullable=False)
    mime_type         = Column(String, nullable=False)
    created_at        = Column(DateTime, default=_now, index=True)


class MalpracticeIncident(Base):
    __tablename__ = "malpractice_incidents"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    question_id       = Column(Integer, nullable=True)
    incident_type     = Column(String, nullable=False)
    severity          = Column(String, nullable=False)  # low, medium, high, critical
    confidence_score  = Column(Float, nullable=False)
    agent_name        = Column(String, nullable=False)
    reason_text       = Column(Text, nullable=True)
    created_at        = Column(DateTime, default=_now, index=True)


class IncidentEvidence(Base):
    __tablename__ = "incident_evidence"

    id                = Column(Integer, primary_key=True, index=True)
    incident_id       = Column(Integer, nullable=False, index=True)
    evidence_file_id  = Column(Integer, nullable=False, index=True)
    sequence_order    = Column(Integer, default=0)


class RoomScan(Base):
    __tablename__ = "room_scans"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    scan_type         = Column(String, nullable=False)  # initial, re-verification
    scan_status       = Column(String, default="pending")  # pending, processing, completed, failed
    verdict           = Column(String, nullable=True)  # pass, fail, warning
    suspicious_items_json = Column(Text, default="{}")
    created_at        = Column(DateTime, default=_now, index=True)
    completed_at      = Column(DateTime, nullable=True)


class RoomScanFrame(Base):
    __tablename__ = "room_scan_frames"

    id                = Column(Integer, primary_key=True, index=True)
    room_scan_id      = Column(Integer, nullable=False, index=True)
    evidence_file_id  = Column(Integer, nullable=False, index=True)
    frame_index       = Column(Integer, nullable=False)
    has_violation     = Column(Boolean, default=False)


class MCQQuestionAnswer(Base):
    __tablename__ = "mcq_question_answers"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    question_id       = Column(Integer, nullable=False)
    selected_answer   = Column(String, nullable=True)
    is_correct        = Column(Boolean, nullable=True)
    time_spent_seconds = Column(Integer, nullable=True)
    answered_at       = Column(DateTime, default=_now)


class AgentDecisionLog(Base):
    __tablename__ = "agent_decision_logs"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    agent_name        = Column(String, nullable=False, index=True)
    detection_type    = Column(String, nullable=False)
    confidence_score  = Column(Float, nullable=False)
    reasoning_text    = Column(Text, nullable=True)
    processing_time_ms = Column(Float, nullable=True)
    incident_id       = Column(Integer, nullable=True, index=True)
    created_at        = Column(DateTime, default=_now, index=True)


class ReconnectLog(Base):
    __tablename__ = "reconnect_logs"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    disconnect_timestamp = Column(DateTime, nullable=False)
    reconnect_timestamp = Column(DateTime, nullable=False)
    gap_duration_seconds = Column(Integer, nullable=False)
    device_fingerprint_before = Column(String, nullable=True)
    device_fingerprint_after = Column(String, nullable=True)
    fingerprint_match = Column(Boolean, nullable=True)
    disconnect_verdict = Column(String, nullable=True)  # clean, suspicious, likely_malpractice, confirmed_malpractice
    gap_video_verdict = Column(String, nullable=True)
    combined_verdict  = Column(String, nullable=True)
    risk_penalty      = Column(Integer, default=0)
    analysis_completed = Column(Boolean, default=False)
    created_at        = Column(DateTime, default=_now)


class CameraGap(Base):
    __tablename__ = "camera_gaps"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    reconnect_log_id  = Column(Integer, nullable=True, index=True)
    gap_start         = Column(DateTime, nullable=False)
    gap_end           = Column(DateTime, nullable=False)
    gap_duration_seconds = Column(Integer, nullable=False)
    offline_recording_s3_key = Column(String, nullable=True)
    created_at        = Column(DateTime, default=_now)


class OfflineRecording(Base):
    __tablename__ = "offline_recordings"

    id                = Column(Integer, primary_key=True, index=True)
    session_token     = Column(String, index=True, nullable=False)
    camera_gap_id     = Column(Integer, nullable=True, index=True)
    s3_key            = Column(String, nullable=False, unique=True)
    file_size_bytes   = Column(Integer, nullable=False)
    duration_seconds  = Column(Integer, nullable=True)
    analysis_status   = Column(String, default="pending")  # pending, processing, completed, failed
    analysis_result_json = Column(Text, default="{}")
    created_at        = Column(DateTime, default=_now)


class OfferWorkflow(Base):
    __tablename__ = "offer_workflows"

    id                    = Column(Integer, primary_key=True, index=True)
    application_id        = Column(Integer, unique=True, index=True, nullable=False)
    token                 = Column(String, unique=True, index=True, nullable=False)
    status                = Column(String, default="joining_pending")
    joining_date          = Column(String, nullable=True)
    joining_date_history_json = Column(Text, default="[]")
    onboarding_instructions = Column(Text, default="")
    work_mode             = Column(String, default="")
    employment_type       = Column(String, default="")
    reporting_manager     = Column(String, default="")
    reporting_team        = Column(String, default="")
    compensation_text     = Column(Text, default="")
    offered_compensation  = Column(Text, default="")
    contract_duration_or_notes = Column(Text, default="")
    designation           = Column(String, default="")
    department            = Column(String, default="")
    company_details       = Column(Text, default="")
    work_location         = Column(String, default="")
    hr_contact_details    = Column(Text, default="")
    terms_and_conditions  = Column(Text, default="")
    offer_valid_until     = Column(String, default="")
    candidate_portal_expires_at = Column(DateTime, nullable=True)
    bgv_initiated_at      = Column(DateTime, nullable=True)
    bgv_started_by        = Column(String, default="")
    offer_generated_at    = Column(DateTime, nullable=True)
    unsigned_pdf_path     = Column(String, default="")
    signed_pdf_path       = Column(String, default="")
    offer_sent_at         = Column(DateTime, nullable=True)
    offer_email_to        = Column(String, default="")
    offer_link_opened_at  = Column(DateTime, nullable=True)
    candidate_response    = Column(String, default="")  # accepted | rejected
    candidate_response_at = Column(DateTime, nullable=True)
    candidate_remarks     = Column(Text, default="")
    signature_image_path  = Column(String, default="")
    signature_type        = Column(String, default="")
    candidate_ip          = Column(String, default="")
    candidate_user_agent  = Column(Text, default="")
    hr_final_approval_status = Column(String, default="")  # pending | approved | rejected | on_hold
    hr_final_approval_at  = Column(DateTime, nullable=True)
    hr_final_approver     = Column(String, default="")
    hr_final_approval_reason = Column(Text, default="")
    final_outcome         = Column(String, default="")  # hired | rejected | on_hold
    final_outcome_summary = Column(Text, default="")
    final_recommendation_score = Column(Float, nullable=True)
    onboarding_status     = Column(String, default="")  # pending | in_progress | completed
    onboarding_notes      = Column(Text, default="")
    onboarding_started_at = Column(DateTime, nullable=True)
    onboarding_completed_at = Column(DateTime, nullable=True)
    created_at            = Column(DateTime, default=_now)
    updated_at            = Column(DateTime, default=_now, onupdate=_now)


class WorkflowAuditLog(Base):
    __tablename__ = "workflow_audit_logs"

    id                = Column(Integer, primary_key=True, index=True)
    application_id    = Column(Integer, index=True, nullable=False)
    stage_key         = Column(String, index=True, default="")
    event_type        = Column(String, nullable=False)
    actor_type        = Column(String, default="system")
    actor_email       = Column(String, default="")
    summary           = Column(Text, default="")
    detail_json       = Column(Text, default="{}")
    created_at        = Column(DateTime, default=_now, index=True)


class AssessmentItemResult(Base):
    __tablename__ = "assessment_item_results"

    id                = Column(Integer, primary_key=True, index=True)
    application_id    = Column(Integer, index=True, nullable=False)
    stage_key         = Column(String, index=True, nullable=False)
    source_session_type = Column(String, default="")
    source_session_id = Column(Integer, nullable=True, index=True)
    session_token     = Column(String, index=True, nullable=True)
    item_type         = Column(String, default="question")
    item_key          = Column(String, default="")
    item_order        = Column(Integer, default=0)
    question_text     = Column(Text, default="")
    candidate_answer  = Column(Text, default="")
    correct_answer    = Column(Text, default="")
    ai_summary        = Column(Text, default="")
    manual_comments   = Column(Text, default="")
    marks_awarded     = Column(Float, nullable=True)
    marks_reason      = Column(Text, default="")
    strengths_json    = Column(Text, default="[]")
    weaknesses_json   = Column(Text, default="[]")
    confidence_analysis = Column(Text, default="")
    technical_analysis = Column(Text, default="")
    time_spent_seconds = Column(Float, nullable=True)
    started_at        = Column(DateTime, nullable=True)
    ended_at          = Column(DateTime, nullable=True)
    total_duration_seconds = Column(Float, nullable=True)
    response_latency_seconds = Column(Float, nullable=True)
    meta_json         = Column(Text, default="{}")
    created_at        = Column(DateTime, default=_now)


class ApplicationDocument(Base):
    __tablename__ = "application_documents"

    id                = Column(Integer, primary_key=True, index=True)
    application_id    = Column(Integer, index=True, nullable=False)
    document_type     = Column(String, nullable=False)  # resume | cover_letter
    s3_key            = Column(String, nullable=False, unique=True)
    original_filename = Column(String, nullable=False)
    mime_type         = Column(String, nullable=False)
    file_size_bytes   = Column(Integer, nullable=False, default=0)
    extracted_text    = Column(Text, default="")
    uploaded_at       = Column(DateTime, default=_now, index=True)


class VerificationDocument(Base):
    __tablename__ = "verification_documents"

    id                = Column(Integer, primary_key=True, index=True)
    verification_case_id = Column(Integer, index=True, nullable=False)
    document_type     = Column(String, nullable=False)
    category          = Column(String, nullable=False, default="other")
    required          = Column(Boolean, default=True)
    s3_key            = Column(String, nullable=False, unique=True)
    original_filename = Column(String, nullable=False)
    mime_type         = Column(String, nullable=False)
    file_size_bytes   = Column(Integer, nullable=False, default=0)
    ocr_text          = Column(Text, default="")
    ocr_json          = Column(Text, default="{}")
    ocr_status        = Column(String, default="pending")
    verification_status = Column(String, default="pending")
    uploaded_at       = Column(DateTime, default=_now, index=True)
