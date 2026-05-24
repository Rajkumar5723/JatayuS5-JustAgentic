"""
Canonical multi-round test service.

This service now supports both the newer generic routes and the legacy
frontend contract used by the current shortlisting/coding UI.
"""
from __future__ import annotations

import json
import logging
import sys
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Optional

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import requests
from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.email_utils import send_email, send_coding_result_email
from core.models import Base, CodingSession, Job, TestSession
from core.interview_rounds import parse_rounds_config
from core.proctoring import record_event
from core.room_scan_gate import ensure_initial_room_scan_completed, has_completed_initial_room_scan
from core.runtime_schema import ensure_runtime_schema
from core.workflow import build_coding_items, replace_assessment_items

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

@asynccontextmanager
async def lifespan(_: FastAPI):
    ensure_runtime_schema()
    yield


app = FastAPI(title="Hiresy Multi-Round Test Service", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class CreateTestRequest(BaseModel):
    application_id: int
    job_id: int
    candidate_name: str
    candidate_email: str
    job_title: str = ""
    job_skills: str = ""
    round_type: str = "coding"  # coding | oop | database | api
    duration_mins: int = 60
    total_questions: int = 15
    pass_score: int = 60
    resume_text: str = ""


class SubmitGenericRequest(BaseModel):
    token: str = ""
    answers: Any = None
    submissions: list[dict] = []
    telemetry: dict = {}


class ProctoringEventRequest(BaseModel):
    event_type: str
    payload: dict = {}


class RunCodeRequest(BaseModel):
    code: str = ""
    language: str = ""
    filename: str = ""
    all_files: list[dict[str, Any]] = []


class ChatRequest(BaseModel):
    message: str
    context: dict[str, Any] = {}


class EditRequest(BaseModel):
    instruction: str
    code: str


ROUND_DISPLAY_LABELS = {
    "coding": "Coding Round",
    "oop": "OOP Concepts",
    "database": "Database Design",
    "api": "API Design",
    "vibe": "Vibe Coding",
}

ROUND_SYSTEM_TYPES = {
    "coding": "coding",
    "oop": "oop_concepts",
    "database": "database_design",
    "api": "api_design",
    "vibe": "vibe_coding",
}


def _fallback_problems(job_title: str) -> list[dict]:
    return [
        {
            "id": 1,
            "title": f"Array Pair Sum for {job_title or 'Engineering'}",
            "difficulty": "easy",
            "description": "Given an array of integers and a target value, return the indices of the two numbers that add up to the target.",
            "input_format": "First line: comma-separated integers. Second line: target integer.",
            "output_format": "Two indices as a JSON array.",
            "constraints": ["2 <= n <= 10^4", "Exactly one valid answer exists"],
            "examples": [
                {"input": "2,7,11,15\n9", "output": "[0,1]", "explanation": "2 + 7 = 9"},
                {"input": "3,2,4\n6", "output": "[1,2]", "explanation": "2 + 4 = 6"},
            ],
            "starter_code": {
                "python": "def solution(nums, target):\n    pass\n",
                "javascript": "function solution(nums, target) {\n  return [];\n}\n",
                "java": "class Solution {\n  public int[] solution(int[] nums, int target) {\n    return new int[]{};\n  }\n}\n",
                "cpp": "#include<vector>\nusing namespace std;\nvector<int> solution(vector<int>& nums, int target) {\n  return {};\n}\n",
            },
        },
        {
            "id": 2,
            "title": "Frequency Counter",
            "difficulty": "medium",
            "description": "Return the first non-repeating character from a string. If none exists, return an empty string.",
            "input_format": "One string.",
            "output_format": "Single character.",
            "constraints": ["1 <= len(s) <= 10^5"],
            "examples": [
                {"input": "swiss", "output": "w", "explanation": "w is the first non-repeating character"},
                {"input": "aabb", "output": "", "explanation": "Every character repeats"},
            ],
            "starter_code": {
                "python": "def solution(s):\n    pass\n",
                "javascript": "function solution(s) {\n  return '';\n}\n",
                "java": "class Solution {\n  public String solution(String s) {\n    return \"\";\n  }\n}\n",
                "cpp": "#include<string>\nusing namespace std;\nstring solution(string s) {\n  return \"\";\n}\n",
            },
        },
    ]


def _fallback_questions(round_type: str) -> list[dict]:
    base = {
        "oop": [
            ("Which SOLID principle encourages small focused abstractions?", ["LSP", "SRP", "OCP", "DIP"], 1),
            ("Which pattern is best for one shared instance?", ["Factory", "Singleton", "Observer", "Adapter"], 1),
        ],
        "database": [
            ("What problem does indexing primarily solve?", ["Faster reads", "More storage", "Better backups", "Fewer joins"], 0),
            ("What is 3NF mainly concerned with?", ["Horizontal scaling", "Transitive dependencies", "Deadlocks", "Caching"], 1),
        ],
        "api": [
            ("Which status code best fits resource creation?", ["200", "201", "204", "304"], 1),
            ("What is the best default auth scheme for stateless APIs?", ["Cookies only", "Basic auth", "Bearer token", "FTP"], 2),
        ],
    }
    chosen = base.get(round_type, base["api"])
    questions = []
    for idx, (question, options, correct) in enumerate(chosen, start=1):
        questions.append(
            {
                "id": idx,
                "question": question,
                "options": options,
                "correct_index": correct,
                "is_trap": idx == len(chosen),
            }
        )
    while len(questions) < 15:
        questions.append(
            {
                "id": len(questions) + 1,
                "question": f"{round_type.upper()} authenticity check #{len(questions) + 1}",
                "options": ["A", "B", "C", "D"],
                "correct_index": 0,
                "is_trap": True,
            }
        )
    return questions


def _fallback_vibe_problem(job_title: str, skills: str) -> dict[str, Any]:
    return {
        "id": 1,
        "title": f"Vibe Coding Build for {job_title or 'Software Engineer'}",
        "difficulty": "medium",
        "description": (
            f"Build a small, clean solution for a {job_title or 'software engineering'} candidate. "
            f"Focus on {skills or 'general problem solving'} and return working code plus sensible structure."
        ),
        "examples": [
            {"input": "tasks = ['parse', 'rank', 'notify']", "output": "['notify', 'parse', 'rank']"},
            {"input": "tasks = ['draft']", "output": "['draft']"},
        ],
        "starter_code_text": "def solve(tasks):\n    # sort and return the tasks list\n    return tasks\n",
        "starter_code": "def solve(tasks):\n    # sort and return the tasks list\n    return tasks\n",
        "languages": ["python", "javascript", "typescript", "java"],
    }


def generate_problems(job_title: str, skills: str) -> list[dict]:
    if not settings.GROQ_API_KEY:
        return _fallback_problems(job_title)

    prompt = (
        f'Generate exactly 2 coding interview problems for a "{job_title}" role. '
        f"Skills focus: {skills or 'general software engineering'}.\n"
        "Return ONLY valid JSON with title, difficulty, description, input_format, output_format, constraints, examples, starter_code."
    )
    try:
        res = requests.post(
            settings.GROQ_URL,
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 2500,
            },
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
            timeout=45,
        )
        res.raise_for_status()
        raw = res.json()["choices"][0]["message"]["content"]
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("[")
        end = clean.rfind("]")
        if start == -1 or end == -1:
            return _fallback_problems(job_title)
        problems = json.loads(clean[start : end + 1])
        return problems[:2] if problems else _fallback_problems(job_title)
    except Exception as exc:
        logger.warning("Coding problem generation failed: %s", exc)
        return _fallback_problems(job_title)


def generate_questions(round_type: str, job_title: str, job_skills: str, resume_text: str) -> list[dict]:
    if not settings.GROQ_API_KEY:
        return _fallback_questions(round_type)

    prompt = (
        f"Generate 15 MCQs for a {round_type.upper()} screening round.\n"
        f"Role: {job_title}\nSkills: {job_skills}\nResume context: {resume_text[:1500]}\n"
        "Include 3 authenticity trap questions. Return ONLY JSON list with id, question, options, correct_index, is_trap."
    )
    try:
        res = requests.post(
            settings.GROQ_URL,
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3,
                "max_tokens": 2500,
            },
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}"},
            timeout=45,
        )
        res.raise_for_status()
        raw = res.json()["choices"][0]["message"]["content"]
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("[")
        end = clean.rfind("]")
        if start == -1 or end == -1:
            return _fallback_questions(round_type)
        parsed = json.loads(clean[start : end + 1])
        return parsed[:15] if parsed else _fallback_questions(round_type)
    except Exception as exc:
        logger.warning("Question generation failed: %s", exc)
        return _fallback_questions(round_type)


def generate_vibe_problem(job_title: str, skills: str) -> dict[str, Any]:
    if not settings.GROQ_API_KEY:
        return _fallback_vibe_problem(job_title, skills)

    prompt = (
        f'Create a single open-ended coding challenge for a "{job_title}" role. '
        f"Relevant skills: {skills or 'general software engineering'}.\n"
        "It should feel realistic, practical, and solvable in 30-45 minutes.\n"
        "Return ONLY valid JSON with: title, difficulty, description, examples, starter_code, languages."
    )
    try:
        res = requests.post(
            settings.GROQ_URL,
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.4,
                "max_tokens": 1800,
            },
            headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
            timeout=45,
        )
        res.raise_for_status()
        raw = res.json()["choices"][0]["message"]["content"]
        clean = raw.strip().replace("```json", "").replace("```", "").strip()
        start = clean.find("{")
        end = clean.rfind("}")
        if start == -1 or end == -1:
            return _fallback_vibe_problem(job_title, skills)
        parsed = json.loads(clean[start : end + 1])
        if not isinstance(parsed, dict):
            return _fallback_vibe_problem(job_title, skills)
        parsed.setdefault("id", 1)
        parsed.setdefault("title", f"Vibe Coding Build for {job_title or 'Software Engineer'}")
        parsed.setdefault("difficulty", "medium")
        parsed.setdefault("description", "")
        parsed.setdefault("examples", [])
        parsed.setdefault("starter_code_text", parsed.get("starter_code") or "")
        parsed.setdefault("starter_code", parsed.get("starter_code_text") or "")
        parsed.setdefault("languages", ["python", "javascript"])
        return parsed
    except Exception as exc:
        logger.warning("Vibe coding generation failed: %s", exc)
        return _fallback_vibe_problem(job_title, skills)


def _safe(session: CodingSession) -> dict[str, Any]:
    summary = json.loads(session.proctoring_json or "{}") if session.proctoring_json else {}
    return {
        "id": session.id,
        "token": session.token,
        "application_id": session.application_id,
        "job_id": session.job_id,
        "candidate_name": session.candidate_name,
        "candidate_email": session.candidate_email,
        "job_title": session.job_title,
        "job_skills": session.job_skills,
        "round_type": session.round_type,
        "duration_mins": session.duration_mins,
        "total_questions": session.total_questions,
        "pass_score": session.pass_score,
        "score": session.score,
        "score_pct": session.score_pct,
        "passed": session.passed,
        "status": session.status,
        "email_sent": session.email_sent,
        "proctoring_risk": session.proctoring_risk,
        "risk_score": session.risk_score,
        "block_reason": session.block_reason,
        "face_continuity_score": session.face_continuity_score,
        "manual_round_url": settings.public_frontend_path(f"/coding/{session.token}"),
        "feedback": summary.get("feedback", ""),
        "reasoning": summary.get("reasoning", ""),
        "created_at": str(session.created_at),
        "submitted_at": str(session.submitted_at) if session.submitted_at else None,
    }


def _candidate_payload(session: CodingSession, *, content_unlocked: bool = True) -> dict[str, Any]:
    if session.round_type == "coding":
        problems = json.loads(session.problems_json or "[]")
        return {
            "token": session.token,
            "candidate_name": session.candidate_name,
            "job_title": session.job_title,
            "duration_mins": session.duration_mins,
            "status": session.status,
            "started_at": str(session.started_at) if session.started_at else None,
            "round_type": session.round_type,
            "problem_count": len(problems),
            "content_locked": not content_unlocked,
            "room_scan_required": not content_unlocked,
            "problems": problems if content_unlocked else [],
        }

    if session.round_type == "vibe":
        problems = json.loads(session.problems_json or "[]")
        problem = problems[0] if problems else {}
        payload = {
            "token": session.token,
            "candidate_name": session.candidate_name,
            "job_title": session.job_title,
            "duration_mins": session.duration_mins,
            "status": session.status,
            "started_at": str(session.started_at) if session.started_at else None,
            "round_type": session.round_type,
            "pass_score": session.pass_score,
            "total_questions": 1,
            "problem_count": 1,
            "content_locked": not content_unlocked,
            "room_scan_required": not content_unlocked,
        }
        if content_unlocked:
            payload.update(
                {
                    "problem_id": problem.get("id", 1),
                    "problem_statement": problem.get("description", ""),
                    "problem_title": problem.get("title", "Vibe Coding"),
                    "starter_code": problem.get("starter_code_text") or problem.get("starter_code") or "",
                    "examples": problem.get("examples", []),
                    "languages": problem.get("languages", ["python", "javascript"]),
                }
            )
        return payload

    questions = []
    for item in json.loads(session.questions_json or "[]"):
        cleaned = dict(item)
        cleaned.pop("correct_index", None)
        questions.append(cleaned)
    return {
        "token": session.token,
        "candidate_name": session.candidate_name,
        "job_title": session.job_title,
        "duration_mins": session.duration_mins,
        "status": session.status,
        "started_at": str(session.started_at) if session.started_at else None,
        "round_type": session.round_type,
        "pass_score": session.pass_score,
        "content_locked": not content_unlocked,
        "room_scan_required": not content_unlocked,
        "questions": questions if content_unlocked else [],
        "total_questions": session.total_questions,
    }


def _send_round_invite(session: CodingSession) -> bool:
    round_label = ROUND_DISPLAY_LABELS.get(session.round_type, f"{session.round_type.upper()} Assessment")
    round_url = settings.public_frontend_path(f"/coding/{session.token}")
    return send_email(
        to=session.candidate_email,
        subject=f"{round_label} Invitation - {session.job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">{round_label} Invitation</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  Hi <strong>{session.candidate_name}</strong>, you have been invited to the next test for
  <strong>{session.job_title}</strong>.
</p>
<p style="margin:0 0 16px;font-size:15px;color:#555;line-height:1.7;">
  Time limit: <strong>{session.duration_mins} minutes</strong>. Please complete this round in one sitting.
</p>
<table cellpadding="0" cellspacing="0" style="margin:20px 0;">
  <tr><td style="background:#111;border-radius:8px;">
    <a href="{round_url}" style="display:inline-block;padding:14px 32px;font-size:15px;font-weight:700;color:#fff;text-decoration:none;">Start {round_label}</a>
  </td></tr>
</table>
<p style="margin:0;font-size:13px;color:#888;">Direct link: {round_url}</p>
""",
        stage="coding_invite",
        application_id=session.application_id,
        coding_session_id=session.id,
        meta={"round_type": session.round_type},
    )


def _reference_face_for(application_id: int, db: Session) -> Optional[str]:
    shortlist = db.query(TestSession).filter(TestSession.application_id == application_id).first()
    if shortlist and shortlist.verification_face_b64:
        return shortlist.verification_face_b64
    coding = (
        db.query(CodingSession)
        .filter(CodingSession.application_id == application_id)
        .order_by(CodingSession.created_at.desc(), CodingSession.id.desc())
        .first()
    )
    return coding.verification_face_b64 if coding else None


def _resolve_job(req: CreateTestRequest, db: Session) -> tuple[Optional[Job], str, str]:
    job = db.query(Job).filter(Job.id == req.job_id).first()
    title = req.job_title or (job.job_name if job else "")
    skills = req.job_skills or (job.skills if job else "") or ""
    return job, title, skills


def _evaluate_mcq(session: CodingSession) -> None:
    questions = json.loads(session.questions_json or "[]")
    answers = json.loads(session.answers_json or "{}")
    correct = 0
    trap_failures = 0
    total_traps = 0

    for idx, question in enumerate(questions):
        qid = str(question.get("id", idx + 1))
        answer = answers.get(qid, answers.get(str(idx), answers.get(idx)))
        if answer == question.get("correct_index"):
            correct += 1
        elif question.get("is_trap"):
            trap_failures += 1
        if question.get("is_trap"):
            total_traps += 1

    total = len(questions) or 1
    session.score = float(correct)
    session.score_pct = round((correct / total) * 100, 2)
    session.passed = session.score_pct >= session.pass_score and session.proctoring_risk != "severe"
    session.authenticity_score = max(0, 100 - (trap_failures * 30))
    summary = json.loads(session.proctoring_json or "{}") if session.proctoring_json else {}
    summary.update(
        {
            "trap_summary": f"{trap_failures}/{total_traps} traps failed",
            "answers_recorded": len(answers),
            "passed_logic": "pass_score_and_not_severe",
        }
    )
    session.proctoring_json = json.dumps(summary)


def _evaluate_coding(session: CodingSession) -> None:
    submissions = json.loads(session.submissions_json or "[]")
    total = len(submissions) or 1
    solved = sum(1 for item in submissions if len((item.get("code") or "").strip()) >= 12)
    session.score = float(solved)
    session.score_pct = round((solved / total) * 100, 2)
    session.passed = session.score_pct >= 50 and session.proctoring_risk != "severe"
    existing = json.loads(session.proctoring_json or "{}") if session.proctoring_json else {}
    existing.update(
        {
            "submissions_recorded": total,
            "non_empty_submissions": solved,
            "passed_logic": "non_empty_code_and_not_severe",
        }
    )
    session.proctoring_json = json.dumps(existing)


def _evaluate_vibe(session: CodingSession) -> None:
    submissions = json.loads(session.submissions_json or "[]")
    primary = submissions[0] if submissions else {}
    code = str(primary.get("code") or "")
    files = primary.get("files") or []
    problems = json.loads(session.problems_json or "[]")
    problem = problems[0] if problems else {}

    feedback = ""
    reasoning = ""
    score = 0
    if code.strip() and settings.GROQ_API_KEY:
        prompt = f"""You are evaluating a candidate's open-ended vibe coding submission.

Problem title: {problem.get("title", "Vibe Coding")}
Problem description:
{problem.get("description", "")}

Examples:
{json.dumps(problem.get("examples", []), indent=2)}

Primary code:
{code}

Additional files:
{json.dumps(files, indent=2)[:4000]}

Return ONLY valid JSON:
{{"score": <0-100>, "feedback": "<short summary>", "reasoning": "<why this score was given>"}}"""
        try:
            res = requests.post(
                settings.GROQ_URL,
                json={
                    "model": settings.GROQ_MODEL,
                    "messages": [{"role": "user", "content": prompt}],
                    "temperature": 0,
                    "max_tokens": 900,
                },
                headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
                timeout=40,
            )
            res.raise_for_status()
            raw = res.json()["choices"][0]["message"]["content"]
            clean = raw.strip().replace("```json", "").replace("```", "").strip()
            start = clean.find("{")
            end = clean.rfind("}")
            parsed = json.loads(clean[start : end + 1]) if start != -1 and end != -1 else {}
            score = int(parsed.get("score", 0))
            feedback = str(parsed.get("feedback") or "")
            reasoning = str(parsed.get("reasoning") or "")
        except Exception as exc:
            logger.warning("Vibe coding evaluation failed: %s", exc)

    if not feedback and not reasoning:
        score = 75 if len(code.strip()) >= 80 else 25 if code.strip() else 0
        feedback = "Submission captured for review." if code.strip() else "No substantial code was submitted."
        reasoning = "Fallback heuristic was used because AI evaluation was unavailable."

    session.score = float(score)
    session.score_pct = float(score)
    session.passed = score >= session.pass_score and session.proctoring_risk != "severe"
    existing = json.loads(session.proctoring_json or "{}") if session.proctoring_json else {}
    existing.update(
        {
            "feedback": feedback,
            "reasoning": reasoning,
            "submitted_files": len(files),
            "passed_logic": "ai_vibe_eval_and_not_severe",
        }
    )
    session.proctoring_json = json.dumps(existing)


def _next_status_for_round(session: CodingSession, db: Session) -> str:
    if not session.passed:
        return "rejected"

    job = db.query(Job).filter(Job.id == session.job_id).first()
    configured = parse_rounds_config(job.rounds if job else None)
    current = ROUND_SYSTEM_TYPES.get(session.round_type, "coding")
    if current in configured:
        current_index = configured.index(current)
        if current_index + 1 < len(configured):
            return f"round_{current_index + 2}"
    return "selected"


def _submit_and_progress(session: CodingSession, db: Session, telemetry: dict[str, Any] | None = None) -> dict[str, Any]:
    session.submitted_at = datetime.now(timezone.utc)
    session.status = "submitted"
    if session.round_type == "coding":
        _evaluate_coding(session)
        passed = session.passed
    elif session.round_type == "vibe":
        _evaluate_vibe(session)
        passed = session.passed
    else:
        # MCQ round progression logic
        _evaluate_mcq(session)
        passed = session.passed

    new_status = _next_status_for_round(session, db)
    try:
        requests.patch(
            f"{settings.MAIN_API_URL}/applications/{session.application_id}/status",
            json={"status": new_status},
            timeout=5,
        )
    except Exception as exc:
        logger.warning("Application status update failed: %s", exc)

    db.commit()

    if session.round_type in {"coding", "vibe"}:
        try:
            send_coding_result_email(
                candidate_email=session.candidate_email,
                candidate_name=session.candidate_name,
                job_title=session.job_title,
                passed=passed,
                application_id=session.application_id,
                coding_session_id=session.id,
                next_round_url=None,
            )
        except Exception as exc:
            logger.error("Failed to send coding result email: %s", exc)
    else:
        try:
            from core.email_utils import send_shortlist_result_email

            send_shortlist_result_email(
                candidate_email=session.candidate_email,
                candidate_name=session.candidate_name,
                job_title=session.job_title,
                passed=passed,
                application_id=session.application_id,
                test_session_id=session.id,
                next_round_url=None,
            )
        except Exception as exc:
            logger.error("Failed to send MCQ result email: %s", exc)
    
    replace_assessment_items(
        db,
        application_id=session.application_id,
        stage_key=session.round_type if session.round_type in {"coding", "vibe"} else f"{session.round_type}_assessment",
        source_session_type="coding",
        source_session_id=session.id,
        session_token=session.token,
        items=build_coding_items(session, telemetry),
    )
    return _safe(session)


@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "coding_test",
        "frontend_url": settings.public_frontend_url,
        "db_mode": settings.DATABASE_MODE,
        "brevo": bool(settings.BREVO_API),
        "email_provider": "brevo",
    }


def _create_session_impl(req: CreateTestRequest, db: Session) -> dict[str, Any]:
    existing = (
        db.query(CodingSession)
        .filter(
            CodingSession.application_id == req.application_id,
            CodingSession.round_type == req.round_type,
        )
        .order_by(CodingSession.created_at.desc(), CodingSession.id.desc())
        .first()
    )
    if existing:
        return {**_safe(existing), "already_exists": True}

    job, job_title, job_skills = _resolve_job(req, db)
    if req.job_id and not job and not req.job_title:
        raise HTTPException(404, "Job not found")

    if req.round_type == "coding":
        problems = generate_problems(job_title, job_skills)
        questions = []
    elif req.round_type == "vibe":
        problems = [generate_vibe_problem(job_title, job_skills)]
        questions = []
    else:
        problems = []
        questions = generate_questions(req.round_type, job_title, job_skills, req.resume_text)

    session = CodingSession(
        token=uuid.uuid4().hex[:24],
        application_id=req.application_id,
        job_id=req.job_id,
        candidate_name=req.candidate_name,
        candidate_email=req.candidate_email,
        job_title=job_title,
        job_skills=job_skills,
        resume_text=req.resume_text,
        round_type=req.round_type,
        problems_json=json.dumps(problems),
        questions_json=json.dumps(questions),
        duration_mins=req.duration_mins,
        total_questions=req.total_questions if req.round_type not in {"coding", "vibe"} else len(problems),
        pass_score=req.pass_score,
        verification_face_b64=_reference_face_for(req.application_id, db),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    session.email_sent = _send_round_invite(session)
    db.commit()
    return {**_safe(session), "already_exists": False}


@app.post("/create")
def create_session(req: CreateTestRequest, db: Session = Depends(get_db)):
    return _create_session_impl(req, db)


@app.post("/coding/create")
def create_legacy_session(req: CreateTestRequest, db: Session = Depends(get_db)):
    return _create_session_impl(req, db)


def _get_session(token: str, db: Session) -> CodingSession:
    session = db.query(CodingSession).filter(CodingSession.token == token).first()
    if not session:
        raise HTTPException(404, "Session not found")
    return session


@app.get("/session/{token}")
def get_session(token: str, db: Session = Depends(get_db)):
    session = _get_session(token, db)
    if session.status == "submitted":
        payload = {
            "status": "submitted",
            "round_type": session.round_type,
            "candidate_name": session.candidate_name,
            "job_title": session.job_title,
        }
        if session.round_type == "vibe":
            summary = json.loads(session.proctoring_json or "{}") if session.proctoring_json else {}
            payload["feedback"] = summary.get("feedback", "")
            payload["reasoning"] = summary.get("reasoning", "")
            payload["score_pct"] = session.score_pct
            payload["passed"] = session.passed
        return payload
    content_unlocked = has_completed_initial_room_scan(db, token) or session.status == "started"
    return _candidate_payload(session, content_unlocked=content_unlocked)


@app.get("/coding/{token}")
def get_legacy_session(token: str, db: Session = Depends(get_db)):
    return get_session(token, db)


@app.post("/session/{token}/start")
def start_session(token: str, db: Session = Depends(get_db)):
    session = _get_session(token, db)
    if session.status == "submitted":
        raise HTTPException(400, "Already submitted")
    ensure_initial_room_scan_completed(db, token)
    if session.status != "started":
        session.status = "started"
        session.started_at = datetime.now(timezone.utc)
        db.commit()
    return {
        "started_at": str(session.started_at),
        "duration_mins": session.duration_mins,
        **_candidate_payload(session, content_unlocked=True),
    }


@app.post("/coding/{token}/start")
def start_legacy_session(token: str, db: Session = Depends(get_db)):
    return start_session(token, db)


def _submit_for_token(token: str, body: dict, db: Session) -> dict[str, Any]:
    session = _get_session(token, db)
    if session.status == "submitted":
        raise HTTPException(400, "Already submitted")
    ensure_initial_room_scan_completed(db, token)

    if session.round_type in {"coding", "vibe"}:
        session.submissions_json = json.dumps(body.get("submissions") or [])
    else:
        answers = body.get("answers") or {}
        if isinstance(answers, list):
            answers = {str(idx + 1): ans for idx, ans in enumerate(answers)}
        session.answers_json = json.dumps(answers)

    return _submit_and_progress(session, db, body.get("telemetry") or {})


@app.post("/submit")
def submit_generic(body: SubmitGenericRequest, db: Session = Depends(get_db)):
    if not body.token:
        raise HTTPException(400, "token required")
    payload = body.model_dump()
    return _submit_for_token(body.token, payload, db)


@app.post("/coding/{token}/submit")
def submit_legacy(token: str, body: dict, db: Session = Depends(get_db)):
    return _submit_for_token(token, body, db)


@app.post("/coding/{token}/proctoring/event")
def record_proctoring(token: str, body: ProctoringEventRequest, db: Session = Depends(get_db)):
    session = _get_session(token, db)
    summary = record_event(
        db,
        session=session,
        event_type=body.event_type,
        payload=body.payload,
        round_name=session.round_type,
        application_id=session.application_id,
        coding_session_id=session.id,
    )
    return summary


def _ensure_vibe_session_ready(token: str, db: Session) -> CodingSession:
    session = _get_session(token, db)
    if session.round_type != "vibe":
        raise HTTPException(400, "Only vibe coding rounds support this action")
    ensure_initial_room_scan_completed(db, token)
    if session.status != "started":
        raise HTTPException(400, "Start the verified coding round before using this tool.")
    return session


@app.post("/coding/{token}/run")
def run_vibe_code(token: str, body: RunCodeRequest, db: Session = Depends(get_db)):
    session = _ensure_vibe_session_ready(token, db)
    problems = json.loads(session.problems_json or "[]")
    problem = problems[0] if problems else {}
    examples = json.dumps(problem.get("examples", []), indent=2)

    if not settings.GROQ_API_KEY:
        expected = ""
        example_rows = problem.get("examples", [])
        if example_rows:
            expected = str(example_rows[0].get("output", ""))
        return {
            "passed": bool(body.code.strip()),
            "actual_output": expected if body.code.strip() else "",
            "expected_output": expected,
            "error": None if body.code.strip() else "No code submitted",
        }

    prompt = f"""You are simulating a vibe coding execution review.

Problem: {problem.get("description", "")}
Examples:
{examples}

Candidate code:
{body.code}

Return ONLY valid JSON:
{{"passed": <true|false>, "actual_output": "<string>", "expected_output": "<string>", "error": "<string or null>"}}"""
    res = requests.post(
        settings.GROQ_URL,
        json={
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "max_tokens": 500,
        },
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
        timeout=30,
    )
    res.raise_for_status()
    raw = res.json()["choices"][0]["message"]["content"]
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(500, "Invalid AI response")
    return json.loads(clean[start : end + 1])


@app.post("/coding/{token}/chat")
def chat_vibe_assistant(token: str, body: ChatRequest, db: Session = Depends(get_db)):
    session = _ensure_vibe_session_ready(token, db)
    problems = json.loads(session.problems_json or "[]")
    problem = problems[0] if problems else {}

    if not settings.GROQ_API_KEY:
        return {"reply": "AI chat is unavailable right now. Keep coding and submit when you're ready."}

    prompt = f"""You are helping with a vibe coding round.
Problem: {problem.get("description", "")}
Current code: {body.context.get("code", "")}

Answer the candidate's question directly and concisely. Use code blocks only when needed."""
    res = requests.post(
        settings.GROQ_URL,
        json={
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": prompt},
                {"role": "user", "content": body.message},
            ],
            "temperature": 0.4,
            "max_tokens": 700,
        },
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
        timeout=30,
    )
    res.raise_for_status()
    return {"reply": res.json()["choices"][0]["message"]["content"]}


@app.post("/coding/{token}/edit")
def edit_vibe_code(token: str, body: EditRequest, db: Session = Depends(get_db)):
    session = _ensure_vibe_session_ready(token, db)
    problems = json.loads(session.problems_json or "[]")
    problem = problems[0] if problems else {}

    if not settings.GROQ_API_KEY:
        return {
            "new_code": body.code,
            "explanation": "AI edit support is unavailable right now, so the existing code was kept.",
        }

    prompt = f"""Edit the code as instructed for this vibe coding problem.
Problem: {problem.get("description", "")}
Current code:
{body.code}

Instruction:
{body.instruction}

Return ONLY valid JSON:
{{"new_code": "<full updated code>", "explanation": "<short explanation>"}}"""
    res = requests.post(
        settings.GROQ_URL,
        json={
            "model": settings.GROQ_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2,
            "max_tokens": 1200,
        },
        headers={"Authorization": f"Bearer {settings.GROQ_API_KEY}", "Content-Type": "application/json"},
        timeout=30,
    )
    res.raise_for_status()
    raw = res.json()["choices"][0]["message"]["content"]
    clean = raw.strip().replace("```json", "").replace("```", "").strip()
    start = clean.find("{")
    end = clean.rfind("}")
    if start == -1 or end == -1:
        raise HTTPException(500, "Invalid AI response")
    return json.loads(clean[start : end + 1])


@app.get("/coding/application/{app_id}")
def get_by_application(app_id: int, db: Session = Depends(get_db)):
    session = db.query(CodingSession).filter(CodingSession.application_id == app_id).first()
    if not session:
        raise HTTPException(404, "No coding round found")
    return _safe(session)
