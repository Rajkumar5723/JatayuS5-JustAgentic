"""
services/shortlisting_test/app.py
===================================
Shortlisting MCQ Test Service — Port 8002
Generates AI-powered MCQ tests and emails them to candidates.

Run with:  uvicorn services.shortlisting_test.app:app --port 8002 --reload
"""
from __future__ import annotations
import json
import logging
import sys, os
import uuid

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import requests
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import List

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.email_utils import send_email, send_shortlist_result_email
from core.models import Job, TestSession
from core.proctoring import record_event
from core.room_scan_gate import ensure_initial_room_scan_completed, has_completed_initial_room_scan
from core.runtime_schema import ensure_runtime_schema
from core.workflow import build_shortlist_items, replace_assessment_items

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


@asynccontextmanager
async def lifespan(app: FastAPI):
    ensure_runtime_schema()
    yield


app = FastAPI(title="Hiresy Shortlisting Test", version="2.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


# ── Pydantic schemas ──────────────────────────────────────────
class CreateTestRequest(BaseModel):
    application_id:  int
    job_id:          int
    candidate_name:  str
    candidate_email: str
    job_title:       str
    job_skills:      str
    assessment_kind: str = "mcq"
    duration_mins:   int = 20
    total_questions: int = 10
    pass_score:      int = 60


class SubmitAnswersRequest(BaseModel):
    answers: List[int]
    telemetry: dict = {}


class ProctoringEventRequest(BaseModel):
    event_type: str
    payload: dict = {}


# ── Helpers ───────────────────────────────────────────────────
def _assessment_copy(assessment_kind: str | None) -> dict[str, str]:
    kind = (assessment_kind or "mcq").strip().lower()
    if kind == "aptitude":
        return {
            "kind": "aptitude",
            "label": "Aptitude Test",
            "subject_label": "aptitude test",
        }
    return {
        "kind": "mcq",
        "label": "MCQ Test",
        "subject_label": "shortlisting test",
    }


def _generate_questions(job_title: str, skills: str, count: int, assessment_kind: str = "mcq") -> list:
    copy = _assessment_copy(assessment_kind)
    if not settings.GROQ_API_KEY:
        if copy["kind"] == "aptitude":
            base = [
                {
                    "question": "If a train travels 240 km in 4 hours, what is its average speed?",
                    "options": ["40 km/h", "50 km/h", "60 km/h", "80 km/h"],
                    "correct": 2,
                    "skill": "Quantitative Aptitude",
                    "difficulty": "easy",
                    "authenticity_trap": False,
                },
                {
                    "question": "Choose the next item in the series: 3, 6, 12, 24, ?",
                    "options": ["30", "36", "42", "48"],
                    "correct": 3,
                    "skill": "Logical Reasoning",
                    "difficulty": "medium",
                    "authenticity_trap": True,
                },
            ]
        else:
            base = [
                {
                    "question": f"{job_title}: what is the most suitable Python data structure for key lookups?",
                    "options": ["list", "tuple", "dict", "set"],
                    "correct": 2,
                    "skill": "Python",
                    "difficulty": "easy",
                    "authenticity_trap": False,
                },
                {
                    "question": "Which statement best describes a REST idempotent method?",
                    "options": ["Safe to cache", "Same effect across retries", "Always async", "Requires auth"],
                    "correct": 1,
                    "skill": "API",
                    "difficulty": "medium",
                    "authenticity_trap": True,
                },
            ]
        return (base * max(1, count))[:count]

    focus_rule = (
        "- Focus on quantitative aptitude, logical reasoning, analytical thinking, and verbal comprehension\n"
        if copy["kind"] == "aptitude"
        else "- Focus on technical knowledge, practical problem solving, and real project understanding\n"
    )
    prompt = (
        f'You are a technical interviewer. Generate exactly {count} {copy["subject_label"]} questions '
        f'for the role "{job_title}". Skills to test: {skills}\n\n'
        'Rules:\n'
        '- Mix: 30% easy, 40% medium, 30% hard\n'
        f"{focus_rule}"
        '- Include 2-3 authenticity trap questions that only prepared candidates would answer correctly\n'
        '- Each question has exactly 4 options\n'
        '- Exactly one correct answer (0-indexed: 0=A, 1=B, 2=C, 3=D)\n'
        '- Questions must verify genuine working knowledge, not just textbook answers\n\n'
        'Return ONLY a valid JSON array, no markdown:\n'
        '[{"question":"...","options":["A","B","C","D"],"correct":0,'
        '"explanation":"...","skill":"Python","difficulty":"easy","authenticity_trap":false}]'
    )
    res = requests.post(
        settings.GROQ_URL,
        json={"model": settings.GROQ_MODEL,
              "messages": [{"role": "user", "content": prompt}],
              "temperature": 0.4, "max_tokens": 3000},
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}",
                 "Content-Type": "application/json"},
        timeout=45,
    )
    res.raise_for_status()
    raw = res.json()["choices"][0]["message"]["content"]
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    s, e = clean.find("["), clean.rfind("]")
    if s == -1 or e == -1:
        raise RuntimeError(f"No JSON array in response: {clean[:300]}")

    questions = json.loads(clean[s:e + 1])
    valid = []
    for q in questions:
        if not isinstance(q, dict):
            continue
        if not all(k in q for k in ["question", "options", "correct"]):
            continue
        if not isinstance(q["options"], list) or len(q["options"]) != 4:
            continue
        q["correct"] = max(0, min(3, int(q["correct"])))
        valid.append(q)
    if not valid:
        raise RuntimeError("No valid questions parsed")
    return valid[:count]


def _safe(t: TestSession) -> dict:
    copy = _assessment_copy(t.assessment_kind)
    return {
        "id": t.id, "token": t.token, "application_id": t.application_id,
        "candidate_name": t.candidate_name, "candidate_email": t.candidate_email,
        "job_title": t.job_title, "total_questions": t.total_questions,
        "duration_mins": t.duration_mins, "pass_score": t.pass_score,
        "score": t.score, "score_pct": t.score_pct, "passed": t.passed,
        "status": t.status, "email_sent": t.email_sent,
        "assessment_kind": copy["kind"],
        "title": copy["label"],
        "proctoring_risk": t.proctoring_risk,
        "risk_score": t.risk_score,
        "block_reason": t.block_reason,
        "face_continuity_score": t.face_continuity_score,
        "manual_round_url": settings.public_frontend_path(f"/test/{t.token}"),
        "created_at": str(t.created_at),
        "submitted_at": str(t.submitted_at) if t.submitted_at else None,
    }


def _send_test_email(test: TestSession) -> bool:
    test_url = settings.public_frontend_path(f"/test/{test.token}")
    copy = _assessment_copy(test.assessment_kind)
    return send_email(
        to=test.candidate_email,
        subject=f"Your {copy['label']} — {test.job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">
  Your {copy['label']} is Ready
</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{test.candidate_name}</strong>, please complete the {copy['subject_label']}
  for <strong>{test.job_title}</strong> using the link below.
</p>
<p style="margin:0 0 28px;font-size:16px;color:#444;line-height:1.7;">
  The test has <strong>{test.total_questions} questions</strong> and a time limit of
  <strong>{test.duration_mins} minutes</strong>. The timer starts when you open the link.
</p>
<table cellpadding="0" cellspacing="0" style="margin-bottom:28px;">
  <tr><td style="background:#ff4400;border-radius:8px;">
    <a href="{test_url}" style="display:inline-block;padding:14px 36px;font-size:16px;
       font-weight:700;color:#fff;text-decoration:none;">Start Test</a>
  </td></tr>
</table>
<p style="margin:0 0 8px;font-size:13px;color:#999;">Or copy this link:</p>
<p style="margin:0 0 32px;font-size:13px;color:#888;word-break:break-all;">{test_url}</p>
<p style="margin:0;font-size:15px;color:#777;line-height:1.6;">
  Best of luck,<br><strong>The Hiresy Hiring Team</strong>
</p>""",
        stage="shortlisting_test",
        application_id=test.application_id,
        test_session_id=test.id,
    )


# ── Endpoints ─────────────────────────────────────────────────
@app.get("/health")
def health():
    return {
        "status": "ok", "model": settings.GROQ_MODEL,
        "brevo": bool(settings.BREVO_API),
        "email_provider": "brevo",
        "groq": bool(settings.GROQ_API_KEY),
        "frontend_url": settings.public_frontend_url,
        "db_mode": settings.DATABASE_MODE,
    }


@app.post("/tests/create")
def create_test(req: CreateTestRequest, db: Session = Depends(get_db)):
    req.assessment_kind = _assessment_copy(req.assessment_kind)["kind"]
    existing = db.query(TestSession).filter(
        TestSession.application_id == req.application_id,
        TestSession.assessment_kind == req.assessment_kind,
    ).first()
    if existing:
        return {**_safe(existing), "already_exists": True}

    try:
        questions = _generate_questions(
            req.job_title,
            req.job_skills,
            req.total_questions,
            req.assessment_kind,
        )
    except Exception as exc:
        raise HTTPException(500, f"Question generation failed: {exc}")

    token = str(uuid.uuid4()).replace("-", "")[:24]
    test  = TestSession(
        token=token, application_id=req.application_id, job_id=req.job_id,
        candidate_name=req.candidate_name, candidate_email=req.candidate_email,
        job_title=req.job_title, job_skills=req.job_skills,
        assessment_kind=req.assessment_kind,
        questions_json=json.dumps(questions),
        duration_mins=req.duration_mins, total_questions=req.total_questions,
        pass_score=req.pass_score,
    )
    db.add(test)
    db.commit()
    db.refresh(test)

    sent = _send_test_email(test)
    test.email_sent = sent
    db.commit()
    return {**_safe(test), "already_exists": False, "email_sent": sent, "token": token}


@app.get("/tests/job/{job_id}")
def get_tests_for_job(job_id: int, db: Session = Depends(get_db)):
    return [_safe(t) for t in db.query(TestSession).filter(TestSession.job_id == job_id).all()]


@app.get("/tests/application/{app_id}")
def get_test_for_application(app_id: int, db: Session = Depends(get_db)):
    t = (
        db.query(TestSession)
        .filter(TestSession.application_id == app_id)
        .order_by(TestSession.created_at.desc(), TestSession.id.desc())
        .first()
    )
    if not t:
        raise HTTPException(404, "No test found")
    return _safe(t)


@app.get("/test/{token}")
def get_test(token: str, db: Session = Depends(get_db)):
    t = db.query(TestSession).filter(TestSession.token == token).first()
    if not t:
        raise HTTPException(404, "Test not found")
    copy = _assessment_copy(t.assessment_kind)
    if t.status == "submitted":
        return {
            "status": "submitted", "score_pct": t.score_pct, "passed": t.passed,
            "score": t.score, "total": t.total_questions,
            "candidate_name": t.candidate_name, "job_title": t.job_title,
            "pass_score": t.pass_score,
            "assessment_kind": copy["kind"],
            "title": copy["label"],
        }
    content_unlocked = has_completed_initial_room_scan(db, token) or t.status == "started"
    questions = json.loads(t.questions_json)
    safe_qs   = [
        {"question": q["question"], "options": q["options"],
         "skill": q.get("skill", ""), "difficulty": q.get("difficulty", "medium")}
        for q in questions
    ]
    return {
        "token": token, "candidate_name": t.candidate_name, "job_title": t.job_title,
        "duration_mins": t.duration_mins, "total_questions": t.total_questions,
        "pass_score": t.pass_score, "status": t.status,
        "assessment_kind": copy["kind"],
        "title": copy["label"],
        "content_locked": not content_unlocked,
        "room_scan_required": not content_unlocked,
        "questions": safe_qs if content_unlocked else [],
    }


@app.post("/test/{token}/start")
def start_test(token: str, db: Session = Depends(get_db)):
    t = db.query(TestSession).filter(TestSession.token == token).first()
    if not t:
        raise HTTPException(404, "Test not found")
    if t.status == "submitted":
        raise HTTPException(400, "Already submitted")
    ensure_initial_room_scan_completed(db, token)
    copy = _assessment_copy(t.assessment_kind)
    if t.status != "started":
        t.status     = "started"
        t.started_at = datetime.now(timezone.utc)
        db.commit()
    questions = json.loads(t.questions_json)
    safe_qs = [
        {"question": q["question"], "options": q["options"],
         "skill": q.get("skill", ""), "difficulty": q.get("difficulty", "medium")}
        for q in questions
    ]
    return {
        "started_at": str(t.started_at),
        "duration_mins": t.duration_mins,
        "token": token,
        "candidate_name": t.candidate_name,
        "job_title": t.job_title,
        "total_questions": t.total_questions,
        "pass_score": t.pass_score,
        "assessment_kind": copy["kind"],
        "title": copy["label"],
        "status": t.status,
        "content_locked": False,
        "room_scan_required": False,
        "questions": safe_qs,
    }


@app.post("/test/{token}/proctoring/event")
def test_proctoring_event(token: str, req: ProctoringEventRequest, db: Session = Depends(get_db)):
    t = db.query(TestSession).filter(TestSession.token == token).first()
    if not t:
        raise HTTPException(404, "Test not found")
    return record_event(
        db,
        session=t,
        event_type=req.event_type,
        payload=req.payload,
        round_name="shortlisting",
        application_id=t.application_id,
        test_session_id=t.id,
    )


@app.post("/test/{token}/submit")
def submit_test(token: str, req: SubmitAnswersRequest, db: Session = Depends(get_db)):
    t = db.query(TestSession).filter(TestSession.token == token).first()
    if not t:
        raise HTTPException(404, "Test not found")
    if t.status == "submitted":
        raise HTTPException(400, "Already submitted")
    ensure_initial_room_scan_completed(db, token)

    questions = json.loads(t.questions_json)
    correct   = sum(
        1 for i, q in enumerate(questions)
        if i < len(req.answers) and int(req.answers[i]) == int(q["correct"])
    )
    total  = len(questions)
    pct    = round((correct / total) * 100)
    passed = pct >= t.pass_score and t.proctoring_risk != "severe"

    t.answers_json = json.dumps(req.answers)
    t.score        = correct
    t.score_pct    = pct
    t.passed       = passed
    t.status       = "submitted"
    t.submitted_at = datetime.now(timezone.utc)
    t.proctoring_json = json.dumps(
        {
            "result_score_pct": pct,
            "passed_logic": "pass_score_and_not_severe",
            "risk_level": t.proctoring_risk,
            "risk_score": t.risk_score,
            "block_reason": t.block_reason,
        }
    )
    db.commit()
    replace_assessment_items(
        db,
        application_id=t.application_id,
        stage_key=f"{t.assessment_kind or 'mcq'}_test",
        source_session_type="shortlisting",
        source_session_id=t.id,
        session_token=t.token,
        items=build_shortlist_items(t, req.telemetry or {}),
    )

    # Update application pipeline status and get next round link
    new_status = "round_2" if passed else "rejected"
    next_round_url = None
    
    try:
        # Get job information for dynamic round generation
        job = db.query(Job).filter(Job.id == t.job_id).first()
        
        # Update status via API (this will trigger email with proper next_round_url)
        requests.patch(
            f"{settings.MAIN_API_URL}/applications/{t.application_id}/status",
            json={"status": new_status}, timeout=5,
        )
        
        # Generate next round link using dynamic interview configuration
        if passed and job:
            from core.interview_rounds import generate_next_round_link
            next_round_url = generate_next_round_link(
                application_id=t.application_id,
                job_id=t.job_id,  # Added job_id
                application_status=new_status,
                candidate_name=t.candidate_name,
                candidate_email=t.candidate_email,
                job_title=t.job_title,
                job_skills=t.job_skills or "",
                hr_email=job.posted_by if job else "",
                rounds_config=job.rounds if job else None,
            )
    except Exception as exc:
        logger.warning("Status update or round link generation failed: %s", exc)

    # Send result email to candidate (with next round link if passed)
    # Note: The applications router also sends an email, but this one is more specific
    # to the shortlisting test result, so we keep both
    try:
        copy = _assessment_copy(t.assessment_kind)
        send_shortlist_result_email(
            candidate_email=t.candidate_email,
            candidate_name=t.candidate_name,
            job_title=t.job_title,
            passed=passed,
            application_id=t.application_id,
            test_session_id=t.id,
            next_round_url=next_round_url,
            assessment_label=copy["label"],
        )
    except Exception as exc:
        logger.error("Failed to send shortlist result email: %s", exc)

    return {
        "score": correct, "total": total, "score_pct": pct,
        "passed": passed, "pass_score": t.pass_score,
    }
