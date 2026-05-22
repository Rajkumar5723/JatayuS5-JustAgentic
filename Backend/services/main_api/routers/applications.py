"""
services/main_api/routers/applications.py
==========================================
Submit / retrieve / update pipeline applications.
Also triggers async AI evaluation after submission.
"""
from __future__ import annotations
import json
import logging
import os
import re
import requests
import uuid
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.document_pipeline import extract_document_text, store_document_bytes
from core.email_utils import send_api_status_update_email
from core.evidence_storage import EvidenceStorageService
from core.models import Application, ApplicationDocument, Job, TestSession, CodingSession
from core.profile_enrichment import (
    fetch_github_light as _shared_fetch_github_light,
    fetch_leetcode_light as _shared_fetch_leetcode_light,
    normalize_eval_profiles,
)
from core.s3_manager import get_s3_manager

router = APIRouter(tags=["applications"])
logger = logging.getLogger(__name__)


def _component(score: float, reasoning: str, signals: list[str] | None = None) -> dict[str, Any]:
    return {
        "score": int(max(0, min(100, round(score)))),
        "reasoning": reasoning,
        "signals": signals or [],
    }


def _extract_username(pattern: str, value: str) -> str:
    match = re.search(pattern, value or "", re.IGNORECASE)
    return match.group(1) if match else ""


def _score_from_skill_overlap(resume_text: str, job_description: str) -> tuple[int, list[str]]:
    resume_lower = (resume_text or "").lower()
    skills_text = ""
    if "skills:" in (job_description or "").lower():
        skills_text = re.split(r"skills:", job_description, flags=re.IGNORECASE, maxsplit=1)[-1]
    required = [
        item.strip().lower()
        for item in re.split(r"[,;/\n]", skills_text)
        if item.strip()
    ]
    matched = [skill for skill in required if skill and skill in resume_lower]
    if required:
        ratio = len(matched) / max(1, len(required))
        return int(55 + (ratio * 40)), matched[:6]
    baseline = 75 if len(resume_text or "") > 1200 else 55
    return baseline, []


def _fetch_github_light(github_url: str) -> dict[str, Any]:
    return _shared_fetch_github_light(github_url)


def _fetch_leetcode_light(leetcode_url: str) -> dict[str, Any]:
    return _shared_fetch_leetcode_light(leetcode_url)


def _run_lightweight_evaluation(eval_payload: dict[str, Any]) -> dict[str, Any]:
    resume_text = eval_payload.get("resume_text", "")
    job_description = eval_payload.get("job_description", "")
    resume_score, matched_skills = _score_from_skill_overlap(resume_text, job_description)

    github_raw = _fetch_github_light(eval_payload.get("github_url", ""))
    github_repos = int(github_raw.get("public_repos") or github_raw.get("total_repos") or 0)
    github_stars = int(github_raw.get("total_stars") or 0)
    github_score = 0 if not github_raw else min(90, 35 + github_repos * 2 + github_stars)

    leetcode_raw = _fetch_leetcode_light(eval_payload.get("leetcode_url", ""))
    lc_total = int(leetcode_raw.get("total") or 0)
    lc_hard = int(leetcode_raw.get("hard") or 0)
    if lc_total >= 300 or lc_hard >= 40:
        leetcode_score = 85
    elif lc_total >= 100:
        leetcode_score = 60
    elif lc_total >= 40:
        leetcode_score = 50
    elif lc_total > 0:
        leetcode_score = 35
    else:
        leetcode_score = 0

    linkedin_score = 80 if eval_payload.get("linkedin_url") else 45
    role_score = min(95, resume_score + (8 if matched_skills else 0))

    component_scores = {
        "resume": _component(
            resume_score,
            "Resume was scored with lightweight skill-overlap and profile-strength checks.",
            [f"Matched skill: {skill}" for skill in matched_skills[:3]],
        ),
        "github": _component(
            github_score,
            "GitHub score is based on public repository count and stars from the GitHub API.",
            [f"Public repos: {github_repos}", f"Stars: {github_stars}"],
        ),
        "leetcode": _component(
            leetcode_score,
            "LeetCode score is based on solved problem count and hard problem count.",
            [f"Total solved: {lc_total}", f"Hard solved: {lc_hard}"],
        ),
        "linkedin": _component(
            linkedin_score,
            "LinkedIn profile URL was provided and used as a professional-presence signal.",
            [eval_payload.get("linkedin_url", "")] if eval_payload.get("linkedin_url") else [],
        ),
        "role_match": _component(
            role_score,
            "Role match is based on required skill overlap between the job description and resume.",
            [f"Matched {len(matched_skills)} required skill(s)"],
        ),
    }

    weights = {"resume": 0.35, "github": 0.15, "leetcode": 0.15, "linkedin": 0.20, "role_match": 0.15}
    final_score = round(sum(component_scores[key]["score"] * weight for key, weight in weights.items()), 1)
    recommendation = "Strong Hire" if final_score >= 85 else "Hire" if final_score >= 70 else "Borderline" if final_score >= 60 else "No Hire"
    summary = (
        "Lightweight production evaluation completed successfully. "
        f"Resume/role score: {resume_score}, GitHub score: {component_scores['github']['score']}, "
        f"LeetCode score: {component_scores['leetcode']['score']}."
    )
    return {
        "hiring_recommendation": recommendation,
        "final_score": final_score,
        "confidence_factor": 0.9,
        "formula_calculation": " + ".join(f"({component_scores[key]['score']}*{weight:.2f})" for key, weight in weights.items()),
        "component_scores": component_scores,
        "github_raw": github_raw,
        "leetcode_raw": leetcode_raw,
        "summary": summary,
        "inconsistencies": [],
        "debate_content": {
            "panel_reasoning": summary,
            "weight_adjustments": {},
            "inconsistencies_flagged": [],
            "name_consistency": [],
            "names_found": {},
        },
        "role_matching": {"missing_skills": []},
        "evaluation_mode": "lightweight_production",
    }


def _app_doc_payload(storage: EvidenceStorageService | None, row: ApplicationDocument) -> dict[str, Any]:
    url = storage.generate_presigned_url(row.s3_key) if storage else row.s3_key
    return {
        "id": row.id,
        "document_type": row.document_type,
        "filename": row.original_filename,
        "mime_type": row.mime_type,
        "file_size_bytes": row.file_size_bytes,
        "storage_key": row.s3_key,
        "storage_url": url,
        "download_url": url,
        "uploaded_at": row.uploaded_at.isoformat() if row.uploaded_at else None,
        "extracted_text": row.extracted_text,
    }
def _list_application_documents(db: Session, app_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == app_id)
        .order_by(ApplicationDocument.uploaded_at.asc(), ApplicationDocument.id.asc())
        .all()
    )
    storage = None
    try:
        storage = EvidenceStorageService(get_s3_manager(), db)
    except Exception:
        storage = None
    return [_app_doc_payload(storage, row) for row in rows]


async def _store_application_document(
    db: Session,
    *,
    application_id: int,
    document_type: str,
    upload,
) -> ApplicationDocument | None:
    if upload is None:
        return None
    payload = await upload.read()
    if not payload:
        return None
    filename = upload.filename or f"{document_type}.pdf"
    mime_type = upload.content_type or "application/octet-stream"
    storage_key, file_size = await store_document_bytes(
        db,
        session_token=f"application-{application_id}",
        document_type=document_type,
        filename=filename,
        mime_type=mime_type,
        payload=payload,
    )
    extracted = extract_document_text(filename, mime_type, payload)
    row = ApplicationDocument(
        application_id=application_id,
        document_type=document_type,
        s3_key=storage_key,
        original_filename=filename,
        mime_type=mime_type,
        file_size_bytes=file_size,
        extracted_text=extracted["text"],
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


# ── Background evaluation trigger ─────────────────────────────
def _run_evaluation(eval_payload: dict) -> dict | None:
    """Call evaluator microservice; use memory-safe fallback on single-service Render."""
    eval_url = f"{settings.eval_api_url}/eval/evaluate"
    try:
        res = requests.post(eval_url, json=eval_payload, timeout=120)
        if res.ok:
            return res.json()
        logger.warning("Eval service HTTP %s: %s", res.status_code, res.text[:200])
    except Exception as exc:
        logger.warning("Eval service unreachable at %s: %s", eval_url, exc)

    try:
        return _run_lightweight_evaluation(eval_payload)
    except Exception as exc:
        logger.error("Lightweight evaluation fallback failed: %s", exc)

    if (os.getenv("ENABLE_HEAVY_EVAL_FALLBACK") or "").strip().lower() not in {"1", "true", "yes"}:
        return None

    try:
        import asyncio
        from services.evaluator.agents.aggregator_agent import orchestrate_evaluation

        github_username = ""
        if eval_payload.get("github_url"):
            match = re.search(r"github\.com/([a-zA-Z0-9-]+)", eval_payload["github_url"], re.IGNORECASE)
            if match:
                github_username = match.group(1)
        leetcode_id = ""
        if eval_payload.get("leetcode_url"):
            match = re.search(r"leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)", eval_payload["leetcode_url"], re.IGNORECASE)
            if match:
                leetcode_id = match.group(1)

        from services.evaluator.scrapers.github_scraper import analyze_github_data
        from services.evaluator.scrapers.leetcode_scraper import fetch_leetcode_profile

        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            gh_data = analyze_github_data(github_username) if github_username else {}
            lc_data = loop.run_until_complete(fetch_leetcode_profile(leetcode_id)) if leetcode_id else {}
            candidate_data = {
                "resume_text": eval_payload.get("resume_text", ""),
                "github_username": github_username,
                "leetcode_id": leetcode_id,
                "linkedin_url": eval_payload.get("linkedin_url") or "Unknown",
                "github_raw": gh_data,
                "leetcode_raw": lc_data,
            }
            result = loop.run_until_complete(
                orchestrate_evaluation(candidate_data, eval_payload.get("job_description", ""))
            )
            if isinstance(result, dict):
                result.setdefault("hiring_recommendation", result.get("recommendation", ""))
                result.setdefault("summary", result.get("debate_summary", ""))
                return result
        finally:
            loop.close()
    except Exception as exc:
        logger.error("In-process evaluation fallback failed: %s", exc)
    return None


def _score_value(value: Any) -> float:
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _load_eval_data(app_entry: Application) -> dict[str, Any]:
    try:
        data = json.loads(app_entry.eval_data or "{}")
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def _ensure_initial_shortlist_invite(
    db: Session,
    app_entry: Application,
    job: Job | None,
    eval_result: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Create/resend the first MCQ/Aptitude invite after AI evaluation."""
    from core.interview_rounds import parse_rounds_config
    from services.shortlisting_test.app import _assessment_copy, _generate_questions, _send_test_email

    result = eval_result or _load_eval_data(app_entry)
    final_score = _score_value(result.get("final_score", app_entry.eval_score))
    if final_score < settings.SHORTLIST_MIN_SCORE:
        return {
            "shortlist_threshold_met": False,
            "test_created": False,
            "test_email_sent": False,
            "assessment_kind": "",
            "test_token": "",
        }

    configured_rounds = parse_rounds_config(job.rounds if job else None)
    first_round = configured_rounds[0] if configured_rounds else "mcq"
    if first_round not in {"mcq", "aptitude"}:
        return {
            "shortlist_threshold_met": True,
            "test_created": False,
            "test_email_sent": False,
            "assessment_kind": first_round,
            "test_token": "",
        }

    assessment_kind = _assessment_copy(first_round)["kind"]
    test = (
        db.query(TestSession)
        .filter(
            TestSession.application_id == app_entry.id,
            TestSession.assessment_kind == assessment_kind,
        )
        .order_by(TestSession.created_at.desc(), TestSession.id.desc())
        .first()
    )
    created = False
    if not test:
        job_title = job.job_name if job else "the position"
        job_skills = job.skills if job else (app_entry.technical_skills or "General")
        questions = _generate_questions(job_title, job_skills, 10, assessment_kind)
        test = TestSession(
            token=uuid.uuid4().hex[:24],
            application_id=app_entry.id,
            job_id=app_entry.job_id,
            candidate_name=app_entry.full_name or "Candidate",
            candidate_email=app_entry.email or "",
            job_title=job_title,
            job_skills=job_skills,
            assessment_kind=assessment_kind,
            questions_json=json.dumps(questions),
            duration_mins=20,
            total_questions=10,
            pass_score=60,
        )
        db.add(test)
        db.commit()
        db.refresh(test)
        created = True

    email_sent = bool(test.email_sent)
    if test.candidate_email and not email_sent:
        email_sent = _send_test_email(test)
        test.email_sent = email_sent
        db.commit()

    if app_entry.status in (None, "", "pending") and test:
        app_entry.status = "round_1"
        db.commit()

    return {
        "shortlist_threshold_met": True,
        "test_created": True,
        "test_created_now": created,
        "test_email_sent": email_sent,
        "assessment_kind": assessment_kind,
        "test_token": test.token if test else "",
        "manual_round_url": settings.public_frontend_path(f"/test/{test.token}") if test else "",
    }


def _trigger_evaluation(app_id: int) -> None:
    """Called as a FastAPI background task after an application is saved."""
    db = None
    try:
        from core.database import SessionLocal
        db = SessionLocal()
        app_entry = db.query(Application).filter(Application.id == app_id).first()
        if not app_entry:
            return

        job = db.query(Job).filter(Job.id == app_entry.job_id).first()
        job_description = (
            f"{job.job_name}\n{job.description}\nSkills: {job.skills}"
            if job else ""
        )
        try:
            extra_fields = json.loads(app_entry.extra_fields or "{}")
        except Exception:
            extra_fields = {}

        def _line(label: str, value: str | None) -> str:
            cleaned = str(value or "").strip()
            return f"{label}: {cleaned}" if cleaned else ""

        education = " ".join(
            part
            for part in [
                str(app_entry.degree_type or "").strip(),
                f"in {str(app_entry.field_of_study or '').strip()}" if app_entry.field_of_study else "",
                f"from {str(app_entry.institution or '').strip()}" if app_entry.institution else "",
            ]
            if part
        )
        experience = str(app_entry.years_exp or "").strip()
        if experience:
            experience = f"{experience} years"

        resume_text_parts = [
            _line("Name", app_entry.full_name),
            _line("Current Title", app_entry.current_title),
            _line("Company", app_entry.company_name),
            _line("Experience", experience),
            _line("Education", education),
            _line("Technical Skills", app_entry.technical_skills),
            _line("Soft Skills", app_entry.soft_skills),
        ]
        if app_entry.cover_letter:
            resume_text_parts.append(f"Cover Letter: {app_entry.cover_letter}")
        if extra_fields.get("resume_text"):
            resume_text_parts.append(f"Resume Extract:\n{extra_fields['resume_text']}")

        eval_payload = {
            "application_id":  app_id,
            "resume_text": "\n".join(part for part in resume_text_parts if part),
            "job_description": job_description,
            "github_url":      app_entry.github_url or "",
            "linkedin_url":    app_entry.linkedin_url or "",
            "leetcode_url":    app_entry.leetcode_url or "",
        }

        result = _run_evaluation(eval_payload)
        if result:
            result = normalize_eval_profiles(
                result,
                github_url=app_entry.github_url,
                leetcode_url=app_entry.leetcode_url,
            )
            invite_result = _ensure_initial_shortlist_invite(db, app_entry, job, result)
            result.update(invite_result)
            app_entry.eval_score          = str(result.get("final_score", ""))
            app_entry.eval_recommendation = result.get("hiring_recommendation", "")
            app_entry.eval_summary        = result.get("summary", "")
            app_entry.eval_data           = json.dumps(result)
            db.commit()
            logger.info("Eval done for app %s → %s", app_id, result.get("final_score"))
        else:
            logger.warning("Evaluation returned no result for app %s", app_id)
    except Exception as exc:
        logger.error("Evaluation failed for app %s: %s", app_id, exc)
    finally:
        if db:
            db.close()


# ── Endpoints ─────────────────────────────────────────────────
@router.post("/applications", summary="Submit a job application")
async def submit_application(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    content_type = request.headers.get("content-type", "").lower()
    payload: dict[str, Any]
    resume_file = None
    cover_letter_file = None
    if "multipart/form-data" in content_type:
        form = await request.form()
        raw_payload = form.get("application_json")
        if not raw_payload:
            raise HTTPException(400, "application_json is required for multipart submissions.")
        try:
            payload = json.loads(str(raw_payload))
        except Exception as exc:
            raise HTTPException(400, f"Invalid application_json payload: {exc}") from exc
        resume_file = form.get("resume_file")
        cover_letter_file = form.get("cover_letter_file")
    else:
        payload = await request.json()

    valid_columns = {c.name for c in Application.__table__.columns}
    known_fields  = {k: v for k, v in payload.items() if k in valid_columns and k != "stage"}
    custom_fields = {k: v for k, v in payload.items() if k not in valid_columns and k != "stage"}

    app_entry = Application(**known_fields)
    app_entry.status = "pending"
    if custom_fields:
        app_entry.extra_fields = json.dumps(custom_fields)

    db.add(app_entry)
    db.commit()
    db.refresh(app_entry)

    if resume_file is not None:
        resume_doc = await _store_application_document(
            db,
            application_id=app_entry.id,
            document_type="resume",
            upload=resume_file,
        )
        if resume_doc:
            app_entry.resume_url = resume_doc.s3_key
            try:
                extra_fields = json.loads(app_entry.extra_fields or "{}")
            except Exception:
                extra_fields = {}
            if resume_doc.extracted_text and not extra_fields.get("resume_text"):
                extra_fields["resume_text"] = resume_doc.extracted_text
            app_entry.extra_fields = json.dumps(extra_fields)
            db.commit()

    if cover_letter_file is not None:
        cover_doc = await _store_application_document(
            db,
            application_id=app_entry.id,
            document_type="cover_letter",
            upload=cover_letter_file,
        )
        if cover_doc and cover_doc.extracted_text and not (app_entry.cover_letter or "").strip():
            app_entry.cover_letter = cover_doc.extracted_text[:15000]
            db.commit()

    background_tasks.add_task(_trigger_evaluation, app_entry.id)
    return {
        "message": "Application submitted!",
        "id": app_entry.id,
        "documents": _list_application_documents(db, app_entry.id),
    }


@router.post("/applications/retry-pending-eval", summary="Re-trigger AI evaluation for all apps missing scores")
def retry_pending_evaluations(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    pending = (
        db.query(Application)
        .filter((Application.eval_score == None) | (Application.eval_score == ""))  # noqa: E711
        .all()
    )
    for app_entry in pending:
        background_tasks.add_task(_trigger_evaluation, app_entry.id)
    return {"message": f"Queued evaluation for {len(pending)} application(s)", "count": len(pending)}


@router.post("/applications/resend-failed-invites", summary="Resend failed first-round candidate invites")
def resend_failed_invites(db: Session = Depends(get_db)):
    applications = (
        db.query(Application)
        .filter(Application.eval_score != None)  # noqa: E711
        .all()
    )
    resent = 0
    created = 0
    failed = 0
    skipped = 0
    results: list[dict[str, Any]] = []

    for app_entry in applications:
        job = db.query(Job).filter(Job.id == app_entry.job_id).first()
        before = (
            db.query(TestSession)
            .filter(TestSession.application_id == app_entry.id)
            .count()
        )
        try:
            eval_data = _load_eval_data(app_entry)
            invite = _ensure_initial_shortlist_invite(db, app_entry, job, eval_data)
            if invite.get("test_created_now"):
                created += 1
            if invite.get("test_email_sent"):
                resent += 1
            elif invite.get("test_created") or invite.get("shortlist_threshold_met"):
                failed += 1
            else:
                skipped += 1
            if eval_data:
                eval_data.update(invite)
                app_entry.eval_data = json.dumps(eval_data)
                db.commit()
            after = (
                db.query(TestSession)
                .filter(TestSession.application_id == app_entry.id)
                .count()
            )
            results.append(
                {
                    "application_id": app_entry.id,
                    "candidate_email": app_entry.email,
                    "created_session": after > before,
                    **invite,
                }
            )
        except Exception as exc:
            failed += 1
            logger.warning("Invite resend failed for app %s: %s", app_entry.id, exc)
            results.append(
                {
                    "application_id": app_entry.id,
                    "candidate_email": app_entry.email,
                    "error": str(exc),
                }
            )

    return {
        "message": "Invite resend completed",
        "count": len(applications),
        "resent_or_already_sent": resent,
        "created": created,
        "failed": failed,
        "skipped": skipped,
        "results": results,
    }


@router.post("/applications/{app_id}/resend-invite", summary="Resend a candidate's first-round invite")
def resend_application_invite(app_id: int, db: Session = Depends(get_db)):
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    invite = _ensure_initial_shortlist_invite(db, app_entry, job, _load_eval_data(app_entry))
    eval_data = _load_eval_data(app_entry)
    eval_data.update(invite)
    app_entry.eval_data = json.dumps(eval_data)
    db.commit()
    return {"message": "Invite resend attempted", "application_id": app_id, **invite}


@router.get("/applications/job/{job_id}/count", summary="Count applications for a job")
def get_application_count(job_id: int, db: Session = Depends(get_db)):
    return {"count": db.query(Application).filter(Application.job_id == job_id).count()}


@router.get("/applications/{job_id}", summary="Get all applications for a job")
def get_applications(job_id: int, db: Session = Depends(get_db)):
    return db.query(Application).filter(Application.job_id == job_id).all()


@router.get("/application/{app_id}", summary="Get a single application (with job name)")
def get_single_application(app_id: int, db: Session = Depends(get_db)):
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    data = {c.name: getattr(app_entry, c.name) for c in app_entry.__table__.columns}
    data["job_name"] = job.job_name if job else "Unknown Position"
    data["job_rounds"] = job.rounds if job else ""
    data["documents"] = _list_application_documents(db, app_id)
    return data


@router.get("/applications/{app_id}/documents", summary="List uploaded application documents for HR review")
def get_application_documents(app_id: int, db: Session = Depends(get_db)):
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    return {
        "application_id": app_id,
        "documents": _list_application_documents(db, app_id),
    }


@router.get("/applications/{app_id}/eval", summary="Get parsed evaluation payload for an application")
def get_application_eval(app_id: int, db: Session = Depends(get_db)):
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    if not app_entry.eval_data:
        payload = normalize_eval_profiles(
            {},
            github_url=app_entry.github_url,
            leetcode_url=app_entry.leetcode_url,
        )
        payload.update({
            "application_id": app_id,
            "eval_summary": app_entry.eval_summary or "",
            "summary": app_entry.eval_summary or "",
        })
        payload.setdefault("component_scores", {})
        return payload

    try:
        payload = json.loads(app_entry.eval_data)
    except Exception:
        payload = {"raw": app_entry.eval_data}

    payload = normalize_eval_profiles(
        payload,
        github_url=app_entry.github_url,
        leetcode_url=app_entry.leetcode_url,
    )
    payload["application_id"] = app_id
    payload["eval_summary"] = app_entry.eval_summary or payload.get("summary", "")
    payload["summary"] = payload.get("summary") or app_entry.eval_summary or ""
    payload.setdefault("github_raw", {})
    payload.setdefault("leetcode_raw", {})
    payload.setdefault("component_scores", {})
    return payload



@router.patch("/applications/{app_id}/status", summary="Update application pipeline status")
def update_status(app_id: int, payload: dict, db: Session = Depends(get_db)):
    from core.interview_rounds import generate_next_round_link, can_select_candidate
    
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    
    old_status = app_entry.status
    new_status = payload.get("status")
    manual_override = bool(payload.get("manual_override"))

    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    if new_status == "selected" and not manual_override:
        ok, msg = can_select_candidate(app_entry.status, job.rounds if job else None)
        if not ok:
            raise HTTPException(400, msg)

    app_entry.status = new_status
    db.commit()
    
    logger.info("Status update for app %s: %s → %s", app_id, old_status, new_status)

    job_title = job.job_name if job else ""
    job_skills = job.skills if job else ""
    hr_email = job.posted_by if job else ""
    
    # Generate next round link using dynamic interview configuration
    next_round_url = None
    if new_status and old_status != new_status:
        next_round_url = generate_next_round_link(
            application_id=app_id,
            job_id=app_entry.job_id,  # Added job_id
            application_status=new_status,
            candidate_name=app_entry.full_name,
            candidate_email=app_entry.email,
            job_title=job_title,
            job_skills=job_skills,
            hr_email=hr_email,
            rounds_config=job.rounds if job else None,
        )
    
    logger.info("Sending status update email for app %s with url: %s", app_id, next_round_url)
    
    # Send email on meaningful status transitions
    try:
        if new_status and old_status != new_status:
            send_api_status_update_email(
                candidate_email=app_entry.email,
                candidate_name=app_entry.full_name,
                job_title=job_title,
                old_status=old_status,
                new_status=new_status,
                application_id=app_id,
                next_round_url=next_round_url,
            )
    except Exception as exc:
        logger.warning("Failed to send status update email: %s", exc)

    return {"message": "Status updated", "status": app_entry.status}


@router.post("/applications/{app_id}/retry-eval", summary="Re-trigger AI evaluation")
def retry_evaluation(
    app_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
):
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    background_tasks.add_task(_trigger_evaluation, app_id)
    return {"message": "Evaluation retrying..."}


@router.get("/applications/{app_id}/tests", summary="Get test history for a candidate")
def get_candidate_test_history(app_id: int, db: Session = Depends(get_db)):
    """
    Fetch all tests (shortlisting, MCQ, coding) for a given application.
    Returns aggregated test data from both TestSession and CodingSession tables.
    """
    tests = []
    
    try:
        # Fetch shortlisting tests (TestSession)
        shortlist_tests = db.query(TestSession).filter(
            TestSession.application_id == app_id
        ).order_by(TestSession.created_at.desc()).all()
        
        for test in shortlist_tests:
            assessment_kind = (test.assessment_kind or "mcq").strip().lower()
            title = "Aptitude Test" if assessment_kind == "aptitude" else "Shortlisting Test"
            # Extract AI reasoning from proctoring JSON
            ai_reason = None
            ai_flags_json = "[]"
            if test.proctoring_json:
                try:
                    proctoring_data = json.loads(test.proctoring_json)
                    ai_reason = proctoring_data.get("summary") or proctoring_data.get("reasoning") or proctoring_data.get("ai_reason")
                    # Also extract flags if available
                    if "flags" in proctoring_data:
                        ai_flags_json = json.dumps(proctoring_data.get("flags", []))
                except (json.JSONDecodeError, TypeError):
                    pass
            
            tests.append({
                "type": "shortlisting",
                "assessment_kind": assessment_kind,
                "title": title,
                "id": test.id,
                "application_id": test.application_id,
                "job_id": test.job_id,
                "token": test.token,
                "manual_round_url": settings.public_frontend_path(f"/test/{test.token}"),
                "score_pct": test.score_pct,
                "passed": test.passed,
                "pass_score": test.pass_score,
                "status": test.status,
                "created_at": test.created_at.isoformat() if test.created_at else None,
                "submitted_at": test.submitted_at.isoformat() if test.submitted_at else None,
                "proctoring_risk": test.proctoring_risk,
                "block_reason": test.block_reason,
                "face_continuity_score": test.face_continuity_score,
                "ai_reason": ai_reason,
                "ai_flags_json": ai_flags_json,
            })
    except Exception as e:
        logger.warning("Error fetching shortlisting tests: %s", e)
    
    try:
        # Fetch coding/MCQ tests (CodingSession) using raw SQL to handle schema issues
        from sqlalchemy import text
        query = text("""
            SELECT 
                id, token, application_id, job_id, candidate_name, candidate_email,
                job_title, job_skills, resume_text, round_type, questions_json,
                problems_json, duration_mins, score,
                score_pct, passed, started_at, submitted_at, created_at, email_sent,
                status, proctoring_risk, risk_score, block_reason, face_continuity_score,
                verification_face_b64, authenticity_score, proctoring_json
            FROM coding_rounds
            WHERE application_id = :app_id
            ORDER BY created_at DESC
        """)
        result = db.execute(query, {"app_id": app_id})
        coding_tests = result.fetchall()
        
        for test_row in coding_tests:
            # Convert row to dict
            test = dict(test_row._mapping)
            
            # Determine title based on round type
            round_titles = {
                "coding": "Coding Round",
                "oop": "OOP Round",
                "database": "Database Round",
                "api": "API Design Round",
            }
            round_type = test.get("round_type", "Unknown")
            title = round_titles.get(round_type, f"{round_type.capitalize()} Round")
            
            # Parse AI reason if available
            ai_reason = None
            ai_flags_json = "[]"
            proctoring_json_str = test.get("proctoring_json")
            if proctoring_json_str:
                try:
                    proctoring_data = json.loads(proctoring_json_str)
                    # Try multiple fields for comprehensive explanation
                    ai_reason = (
                        proctoring_data.get("summary") 
                        or proctoring_data.get("reasoning")
                        or proctoring_data.get("ai_reason")
                        or proctoring_data.get("feedback")
                    )
                    # Extract flags if available
                    if "flags" in proctoring_data:
                        ai_flags_json = json.dumps(proctoring_data.get("flags", []))
                except (json.JSONDecodeError, TypeError):
                    pass
            
            tests.append({
                "type": "coding",
                "round_type": test.get("round_type"),
                "title": title,
                "id": test.get("id"),
                "application_id": test.get("application_id"),
                "job_id": test.get("job_id"),
                "token": test.get("token"),
                "manual_round_url": settings.public_frontend_path(f"/coding/{test.get('token')}") if test.get("token") else None,
                "score_pct": test.get("score_pct"),
                "score": test.get("score"),
                "passed": test.get("passed"),
                "pass_score": test.get("pass_score"),
                "status": test.get("status"),
                "created_at": test.get("created_at").isoformat() if test.get("created_at") else None,
                "submitted_at": test.get("submitted_at").isoformat() if test.get("submitted_at") else None,
                "proctoring_risk": test.get("proctoring_risk"),
                "risk_score": test.get("risk_score"),
                "block_reason": test.get("block_reason"),
                "face_continuity_score": test.get("face_continuity_score"),
                "authenticity_score": test.get("authenticity_score"),
                "ai_reason": ai_reason,
                "ai_flags_json": ai_flags_json,
                "proctoring_json": proctoring_json_str or "{}",
            })
    except Exception as e:
        logger.warning("Error fetching coding tests: %s", e)
    
    # Sort all tests by date (newest first)
    tests.sort(key=lambda x: x["created_at"] or "", reverse=True)
    
    return tests
