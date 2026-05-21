"""
Canonical Live HR service with the embedded live-room workflow used by the
current frontend.
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import string
import sys
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import requests
from fastapi import Depends, FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import SessionLocal, get_db
from core.email_utils import send_email
from core.models import Application, CodingSession, LiveSession, TestSession
from core.proctoring import record_event
from core.runtime_schema import ensure_runtime_schema
from core.workflow import ensure_offer_workflow, log_workflow_event, replace_assessment_items

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

_pool: dict[str, list[WebSocket]] = {}


@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_schema()
    yield


app = FastAPI(title="Hiresy Live HR Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateReq(BaseModel):
    application_id: int
    candidate_name: str
    candidate_email: str
    job_title: str
    job_skills: str = ""
    github_url: str = ""
    github_data: dict = {}
    eval_summary: str = ""
    scheduled_time: str = ""
    hr_email: str = ""
    interview_type: str = "copilot"


class CaptionReq(BaseModel):
    token: str
    text: str
    speaker: str = "candidate"


class OutcomeReq(BaseModel):
    outcome: str
    hr_scores: dict = {}
    hr_reason: str = ""
    manual_decision: str = ""


class LiveEventReq(BaseModel):
    event_type: str
    payload: dict = {}


def _clean_scores(values: dict[str, Any] | None) -> dict[str, float]:
    cleaned: dict[str, float] = {}
    for key, value in (values or {}).items():
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            continue
        cleaned[key] = max(0.0, min(10.0, round(numeric, 2)))
    return cleaned


def make_meet_code(seed: str) -> str:
    hashed = hashlib.sha256(seed.encode()).hexdigest()
    chars = string.ascii_lowercase
    a = "".join(chars[int(hashed[i * 2 : i * 2 + 2], 16) % 26] for i in range(3))
    b = "".join(chars[int(hashed[i * 2 + 6 : i * 2 + 8], 16) % 26] for i in range(4))
    c = "".join(chars[int(hashed[i * 2 + 14 : i * 2 + 16], 16) % 26] for i in range(3))
    return f"{a}-{b}-{c}"


def build_live_room_name(token: str) -> str:
    prefix = (settings.LIVEHR_ROOM_PREFIX or "hiresy").strip().lower() or "hiresy"
    return f"{prefix}-{token}"


def build_live_room_url(room_name: str) -> str:
    room = str(room_name or "").strip().strip("/")
    if not room:
        room = build_live_room_name(uuid.uuid4().hex[:12])
    if room.startswith(("http://", "https://")):
        return room
    if settings.JAAS_APP_ID:
        return f"https://8x8.vc/{settings.JAAS_APP_ID}/{room}"
    return f"https://meet.jit.si/{room}"


def session_room_url(session: LiveSession) -> str:
    room_value = str(session.meet_code or "").strip()
    if room_value.startswith(("http://", "https://")):
        return room_value
    if room_value.count("-") == 2 and len(room_value) == 12:
        return f"https://meet.google.com/{room_value}"
    return build_live_room_url(room_value or build_live_room_name(session.token))


def session_control_url(session: LiveSession) -> str:
    return settings.public_frontend_path(f"/livehr/{session.token}")


def _reference_face_for(application_id: int, db: Session) -> str | None:
    coding = (
        db.query(CodingSession)
        .filter(CodingSession.application_id == application_id)
        .order_by(CodingSession.created_at.desc(), CodingSession.id.desc())
        .first()
    )
    if coding and coding.verification_face_b64:
        return coding.verification_face_b64
    shortlist = db.query(TestSession).filter(TestSession.application_id == application_id).first()
    return shortlist.verification_face_b64 if shortlist else None


def _send_candidate_invite(session: LiveSession) -> bool:
    meet_url = session_room_url(session)
    return send_email(
        to=session.candidate_email,
        subject=f"Live HR Interview Scheduled - {session.job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Live HR Interview Scheduled</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{session.candidate_name}</strong>, you are invited to the live HR interview for
  <strong>{session.job_title}</strong>.
</p>
<p style="margin:0 0 16px;font-size:15px;color:#555;line-height:1.7;">
  Scheduled time: <strong>{session.scheduled_time or 'To be confirmed'}</strong>
</p>
<table cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr><td style="background:#111;border-radius:8px;">
    <a href="{meet_url}" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:700;color:#fff;text-decoration:none;">Join Interview Room</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Live room link: {meet_url}</p>
""",
        stage="live_hr_candidate_invite",
        application_id=session.application_id,
        live_session_id=session.id,
    )


def _send_hr_invite(hr_email: str, session: LiveSession) -> bool:
    control_url = session_control_url(session)
    return send_email(
        to=hr_email,
        subject=f"Interview Ready - {session.candidate_name} / {session.job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Interview Session Created</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  The live HR session for <strong>{session.candidate_name}</strong> is ready.
</p>
<p style="margin:0 0 16px;font-size:15px;color:#555;line-height:1.7;">
  Scheduled time: <strong>{session.scheduled_time or 'Now'}</strong>
</p>
<table cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr><td style="background:#ff4400;border-radius:8px;">
    <a href="{control_url}" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:700;color:#fff;text-decoration:none;">Open Live Interview Desk</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">This desk opens the embedded live room and AI copilot for the interview.</p>
""",
        stage="live_hr_hr_invite",
        application_id=session.application_id,
        live_session_id=session.id,
    )


def _send_live_hr_rejection(session: LiveSession, reason: str) -> bool:
    return send_email(
        to=session.candidate_email,
        subject=f"Application Update - {session.job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">Application Update</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{session.candidate_name}</strong>, thank you for attending the live HR interview for
  <strong>{session.job_title}</strong>. We will not be moving forward to the final verification stage.
</p>
<p style="margin:0;font-size:15px;color:#555;line-height:1.7;">{reason or 'We appreciate your time and effort throughout the process.'}</p>
""",
        stage="live_hr_rejection",
        application_id=session.application_id,
        live_session_id=session.id,
    )


def build_system(session: LiveSession) -> str:
    try:
        github = json.loads(session.github_data or "{}")
    except Exception:
        github = {}
    try:
        scores = json.loads(session.ai_score_json or session.candidate_score or "{}")
    except Exception:
        scores = {}

    repos = "\n".join(
        [
            f"- {repo.get('name')} ({repo.get('language', '?')}) star {repo.get('stars', 0)}"
            for repo in github.get("top_repos", [])[:5]
        ]
    ) or "Not provided"
    score_str = "\n".join(f"- {key}: {value}/10" for key, value in scores.items()) or "Not yet scored"

    return f"""You are Hiresy's live HR copilot for a technical interview.

CANDIDATE: {session.candidate_name}
ROLE: {session.job_title}
SKILLS: {session.job_skills}
AI EVAL SUMMARY: {session.eval_summary or 'N/A'}

TOP PROJECTS:
{repos}

CURRENT AI SCORES:
{score_str}

Return ONLY valid JSON:
{{
  "questions": [
    {{"text": "...", "type": "technical", "priority": "high"}},
    {{"text": "...", "type": "project", "priority": "medium"}},
    {{"text": "...", "type": "behavioral", "priority": "low"}}
  ],
  "scores": {{"technical_depth": 7, "communication": 8, "problem_solving": 6}},
  "insight": "one short observation",
  "flag": ""
}}
"""


def _fallback_ai(question_hint: str = "") -> dict[str, Any]:
    extra = f" about {question_hint}" if question_hint else ""
    return {
        "questions": [
            {"text": f"Can you walk me through a real project decision{extra}?", "type": "project", "priority": "high"},
            {"text": "What tradeoffs did you consider and why?", "type": "technical", "priority": "medium"},
            {"text": "How did you communicate that decision with teammates?", "type": "behavioral", "priority": "low"},
        ],
        "scores": {},
        "insight": "",
        "flag": "",
    }


def get_ai_response(session: LiveSession, new_text: str) -> dict[str, Any]:
    if not settings.GROQ_API_KEY:
        return _fallback_ai(new_text)

    try:
        transcript_tail = (session.transcript or "")[-2500:]
        response = requests.post(
            settings.GROQ_URL,
            json={
                "model": settings.GROQ_MODEL,
                "messages": [
                    {"role": "system", "content": build_system(session)},
                    {
                        "role": "user",
                        "content": f"RECENT TRANSCRIPT:\n{transcript_tail}\n\nNEW INPUT:\n{new_text}\n\nReturn JSON now.",
                    },
                ],
                "temperature": 0.6,
                "max_tokens": 900,
            },
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
            timeout=25,
        )
        response.raise_for_status()
        raw = response.json()["choices"][0]["message"]["content"]
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}")
        if start == -1 or end == -1:
            return _fallback_ai(new_text)
        return json.loads(clean[start : end + 1])
    except Exception as exc:
        logger.error("Live HR AI error: %s", exc)
        return _fallback_ai(new_text)


async def broadcast(token: str, payload: dict[str, Any]) -> None:
    dead: list[WebSocket] = []
    for ws in _pool.get(token, []):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        _pool.get(token, []).remove(ws)


def _session_payload(session: LiveSession) -> dict[str, Any]:
    try:
        github_data = json.loads(session.github_data or "{}")
    except Exception:
        github_data = {}
    try:
        suggestions = json.loads(session.suggestions or "[]")
    except Exception:
        suggestions = []
    try:
        ai_scores = json.loads(session.ai_score_json or session.candidate_score or "{}")
    except Exception:
        ai_scores = {}
    try:
        manual_scores = json.loads(session.manual_score_json or "{}")
    except Exception:
        manual_scores = {}
    try:
        ai_flags = json.loads(session.ai_flags_json or "[]")
    except Exception:
        ai_flags = []
    room_url = session_room_url(session)
    return {
        "token": session.token,
        "meet_code": session.meet_code,
        "meet_url": room_url,
        "room_url": room_url,
        "control_url": session_control_url(session),
        "candidate_name": session.candidate_name,
        "candidate_email": session.candidate_email,
        "job_title": session.job_title,
        "job_skills": session.job_skills,
        "github_url": session.github_url,
        "github_data": github_data,
        "eval_summary": session.eval_summary,
        "scheduled_time": session.scheduled_time,
        "transcript": session.transcript or "",
        "suggestions": suggestions,
        "candidate_score": ai_scores,
        "ai_score": ai_scores,
        "ai_reason": session.ai_reason,
        "ai_flags": ai_flags,
        "manual_score": manual_scores,
        "manual_reason": session.manual_reason,
        "final_summary": session.final_summary,
        "hr_email": session.hr_email,
        "status": session.status,
        "outcome": session.outcome,
        "started_at": session.started_at.isoformat() if session.started_at else None,
    }


async def process_caption(token: str, text: str, speaker: str, db: Session) -> dict[str, Any]:
    session = db.query(LiveSession).filter(LiveSession.token == token).first()
    if not session:
        return {"error": "Session not found"}
    if session.status == "pending":
        session.status = "started"
    if not session.started_at:
        session.started_at = datetime.now(timezone.utc)

    timestamp = datetime.now(timezone.utc).strftime("%H:%M:%S")
    line = f"[{timestamp}][{speaker}] {text}"
    session.transcript = (session.transcript or "") + ("\n" if session.transcript else "") + line
    transcript_lines = [entry for entry in (session.transcript or "").split("\n") if entry.strip()]

    try:
        suggestions = json.loads(session.suggestions or "[]")
    except Exception:
        suggestions = []
    try:
        ai_scores = json.loads(session.ai_score_json or session.candidate_score or "{}")
    except Exception:
        ai_scores = {}
    try:
        ai_flags = json.loads(session.ai_flags_json or "[]")
    except Exception:
        ai_flags = []

    insight = ""
    flag = ""
    if len(transcript_lines) % 3 == 0 or len(text) > 60:
        result = get_ai_response(session, text)
        if result.get("questions"):
            suggestions = result["questions"]
            session.suggestions = json.dumps(suggestions)
        if result.get("scores"):
            ai_scores.update({k: v for k, v in result["scores"].items() if v is not None})
            session.ai_score_json = json.dumps(ai_scores)
            session.candidate_score = json.dumps(ai_scores)
        insight = result.get("insight", "") or ""
        flag = result.get("flag", "") or ""
        if insight:
            session.ai_reason = insight
            session.final_summary = insight
        if flag and flag not in ai_flags:
            ai_flags.append(flag)
            session.ai_flags_json = json.dumps(ai_flags)

    db.commit()
    await broadcast(
        token,
        {
            "type": "update",
            "transcript_line": line,
            "suggestions": suggestions,
            "candidate_score": ai_scores,
            "insight": insight,
            "flag": flag,
            "ai_reason": session.ai_reason,
            "ai_flags": ai_flags,
        },
    )
    return {"ok": True}


def _get_session_or_404(token: str, db: Session) -> LiveSession:
    session = db.query(LiveSession).filter(LiveSession.token == token).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@app.get("/health")
def health():
    return {
        "status": "ok",
        "groq": bool(settings.GROQ_API_KEY),
        "smtp": bool(settings.SMTP_USER),
        "resend": bool(settings.RESEND_API_KEY),
        "email_provider": settings.email_provider,
    }


@app.post("/livehr/session")
def create_session(req: CreateReq, db: Session = Depends(get_db)):
    existing = db.query(LiveSession).filter(LiveSession.application_id == req.application_id).first()
    if existing:
        if req.hr_email:
            existing.hr_email = req.hr_email
            db.commit()
        return {
            "token": existing.token,
            "meet_code": existing.meet_code,
            "meet_url": session_room_url(existing),
            "room_url": session_room_url(existing),
            "control_url": session_control_url(existing),
            "already_exists": True,
        }

    token = uuid.uuid4().hex[:20]
    session = LiveSession(
        token=token,
        meet_code=build_live_room_name(token),
        application_id=req.application_id,
        candidate_name=req.candidate_name,
        candidate_email=req.candidate_email,
        job_title=req.job_title,
        job_skills=req.job_skills,
        github_url=req.github_url,
        github_data=json.dumps(req.github_data or {}),
        eval_summary=req.eval_summary,
        scheduled_time=req.scheduled_time,
        interview_type=req.interview_type,
        hr_email=req.hr_email,
        reference_face_b64=_reference_face_for(req.application_id, db),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    _send_candidate_invite(session)
    if req.hr_email:
        _send_hr_invite(req.hr_email, session)

    return {
        "token": session.token,
        "meet_code": session.meet_code,
        "meet_url": session_room_url(session),
        "room_url": session_room_url(session),
        "control_url": session_control_url(session),
        "already_exists": False,
    }


@app.get("/livehr/session/{token}")
def get_session(token: str, db: Session = Depends(get_db)):
    session = _get_session_or_404(token, db)
    return _session_payload(session)


@app.post("/livehr/caption")
async def receive_caption(req: CaptionReq, db: Session = Depends(get_db)):
    return await process_caption(req.token, req.text, req.speaker, db)


@app.post("/hr/ask")
def ask_hr_question(token: str = Query(...), question: str = Query(""), db: Session = Depends(get_db)):
    session = _get_session_or_404(token, db)
    result = get_ai_response(session, question)
    if result.get("questions"):
        session.suggestions = json.dumps(result["questions"])
        db.commit()
    return result


@app.post("/livehr/session/{token}/outcome")
def set_outcome(token: str, req: OutcomeReq, db: Session = Depends(get_db)):
    session = _get_session_or_404(token, db)
    application = db.query(Application).filter(Application.id == session.application_id).first()
    if not application:
        raise HTTPException(404, "Application not found")

    decision = (req.manual_decision or req.outcome).strip().lower()
    manual_scores = _clean_scores(req.hr_scores)
    session.outcome = decision
    session.status = "ended"
    session.manual_score_json = json.dumps(manual_scores)
    session.manual_reason = req.hr_reason
    session.final_summary = req.hr_reason or session.ai_reason or session.final_summary
    qa_pairs = []
    pending_question = None
    for line in [entry for entry in (session.transcript or "").split("\n") if entry.strip()]:
        lower = line.lower()
        if "[hr]" in lower:
            pending_question = line.split("]", 2)[-1].strip()
        elif "[candidate]" in lower and pending_question:
            qa_pairs.append(
                {
                    "item_type": "interview_exchange",
                    "item_key": len(qa_pairs) + 1,
                    "question_text": pending_question,
                    "candidate_answer": line.split("]", 2)[-1].strip(),
                    "correct_answer": "Manual interview evaluation",
                    "ai_summary": session.ai_reason or "",
                    "manual_comments": req.hr_reason,
                    "marks_reason": req.hr_reason,
                    "meta": {
                        "ai_scorecard": json.loads(session.ai_score_json or session.candidate_score or "{}"),
                        "manual_scorecard": manual_scores,
                    },
                }
            )
            pending_question = None
    if not qa_pairs and (session.transcript or "").strip():
        qa_pairs.append(
            {
                "item_type": "interview_transcript",
                "item_key": 1,
                "question_text": "Live interview transcript",
                "candidate_answer": (session.transcript or "")[-4000:],
                "correct_answer": "Manual interview evaluation",
                "ai_summary": session.ai_reason or "",
                "manual_comments": req.hr_reason,
                "marks_reason": req.hr_reason,
                "meta": {
                    "ai_scorecard": json.loads(session.ai_score_json or session.candidate_score or "{}"),
                    "manual_scorecard": manual_scores,
                    "speaker_mode": "mixed_room_audio",
                },
            }
        )
    db.commit()
    replace_assessment_items(
        db,
        application_id=session.application_id,
        stage_key="final_hr_round",
        source_session_type="live_hr",
        source_session_id=session.id,
        session_token=session.token,
        items=qa_pairs,
    )

    if decision in {"fail", "reject", "rejected"}:
        application.status = "rejected"
        db.commit()
        _send_live_hr_rejection(session, req.hr_reason)
        log_workflow_event(
            db,
            application_id=application.id,
            event_type="live_interview_completed",
            summary="Candidate rejected after live interview.",
            stage_key="final_hr_round",
            actor_type="hr",
            actor_email=session.hr_email,
            detail={"decision": decision, "reason": req.hr_reason},
        )
        return {
            "ok": True,
            "application_status": "rejected",
            "session": _session_payload(session),
        }

    ensure_offer_workflow(db, application.id)
    application.status = "joining_pending"
    db.commit()
    log_workflow_event(
        db,
        application_id=application.id,
        event_type="live_interview_completed",
        summary="Candidate passed live interview and moved to joining setup.",
        stage_key="final_hr_round",
        actor_type="hr",
        actor_email=session.hr_email,
        detail={"decision": decision, "reason": req.hr_reason},
    )
    return {
        "ok": True,
        "application_status": "joining_pending",
        "session": _session_payload(session),
    }


@app.post("/livehr/session/{token}/event")
def record_live_event(token: str, req: LiveEventReq, db: Session = Depends(get_db)):
    session = _get_session_or_404(token, db)
    if req.event_type == "session_opened":
        if session.status == "pending":
            session.status = "started"
        if not session.started_at:
            session.started_at = datetime.now(timezone.utc)
    payload = dict(req.payload or {})
    payload.setdefault("event_origin", "live_room_app")
    db.commit()
    return record_event(
        db,
        session=session,
        event_type=req.event_type,
        payload=payload,
        round_name="live_hr",
        application_id=session.application_id,
        live_session_id=session.id,
    )


async def _ws_handler(websocket: WebSocket, token: str) -> None:
    db = SessionLocal()
    try:
        session = db.query(LiveSession).filter(LiveSession.token == token).first()
        if not session:
            await websocket.close(code=4004)
            return

        await websocket.accept()
        _pool.setdefault(token, []).append(websocket)
        payload = _session_payload(session)
        payload["type"] = "init"
        await websocket.send_json(payload)

        while True:
            raw = await websocket.receive_text()
            data = json.loads(raw)
            if data.get("type") == "caption":
                await process_caption(token, data.get("text", ""), data.get("speaker", "candidate"), db)
    except WebSocketDisconnect:
        logger.info("Live HR websocket disconnected for %s", token)
    finally:
        if websocket in _pool.get(token, []):
            _pool[token].remove(websocket)
        db.close()


@app.websocket("/livehr/ws/{token}")
async def livehr_ws(websocket: WebSocket, token: str):
    await _ws_handler(websocket, token)


@app.websocket("/ws/interview/{token}")
async def interview_ws_alias(websocket: WebSocket, token: str):
    await _ws_handler(websocket, token)
