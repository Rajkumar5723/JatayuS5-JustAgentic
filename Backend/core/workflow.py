from __future__ import annotations

import json
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy.orm import Session

from core.models import (
    AgentDecisionLog,
    Application,
    ApplicationDocument,
    AssessmentItemResult,
    CodingSession,
    EvidenceFile,
    IncidentEvidence,
    LiveSession,
    MalpracticeIncident,
    OfferWorkflow,
    ProctoringEvidence,
    ReconnectLog,
    RoomScan,
    RoomScanFrame,
    TestSession,
    VerificationCase,
    VerificationDocument,
    WorkflowAuditLog,
)
from core.s3_manager import get_s3_manager
from core.evidence_storage import EvidenceStorageService, local_evidence_public_url
from core.config import settings


UTC = timezone.utc
FINAL_HR_STAGE_NAME = "Final HR Round"
HR_LABELS = {"Technical HR", "HR Interview"}
UI_TO_SYSTEM = {
    "mcq test": "mcq",
    "aptitude test": "aptitude",
    "aptitude": "aptitude",
    "screening": "mcq",
    "mcq": "mcq",
    "coding": "coding",
    "basic programming": "coding",
    "oop concepts": "oop_concepts",
    "oop": "oop_concepts",
    "database design": "database_design",
    "database": "database_design",
    "api design": "api_design",
    "api": "api_design",
    "vibe coding": "vibe_coding",
    "vibe coding test": "vibe_coding",
    "vibe": "vibe_coding",
    "technical hr": "technical_hr",
    "technical": "technical_hr",
    "hr interview": "hr_interview",
    "hr round": "hr_interview",
    "hr": "hr_interview",
}
SYSTEM_TO_UI = {
    "mcq": "MCQ Test",
    "aptitude": "Aptitude Test",
    "coding": "Coding",
    "oop_concepts": "OOP Concepts",
    "database_design": "Database Design",
    "api_design": "API Design",
    "vibe_coding": "Vibe Coding",
    "technical_hr": "Technical HR",
    "hr_interview": "HR Interview",
}
POST_INTERVIEW_STATUSES = {
    "joining_pending",
    "offer_pending",
    "offer_sent",
    "offer_signed",
    "approval_pending",
    "hired",
    "on_hold",
    "onboarding_in_progress",
    "onboarding_completed",
}
WORKFLOW_MEDIA_PREVIEW_LIMIT = 8
WORKFLOW_STRING_PREVIEW_LIMIT = 280
WORKFLOW_INLINE_MEDIA_FLAGS = {
    "face_b64": "has_face_capture",
    "screen_b64": "has_screen_capture",
    "snapshot_b64": "has_snapshot_capture",
}
WORKFLOW_MEDIA_SUMMARY_KEYS = ("webcam_snapshots", "screen_snapshots", "meet_snapshots")
DISPLAY_ONLY_ROUND_LABELS = {"group discussion"}


def normalized_stage_title(stage: dict[str, Any], index: int) -> str:
    system_types = {
        str(item.get("system_type") or "").strip()
        for item in stage.get("rounds", [])
    }
    if system_types & {"mcq", "aptitude"}:
        return "Stage 1 - Shortlisting Test"
    if system_types & {"coding", "oop_concepts", "database_design", "api_design", "vibe_coding"}:
        return "Stage 2 - Coding Round"
    if stage.get("is_final_hr") or system_types & {"technical_hr", "hr_interview"}:
        return "Stage 3 - Live Interview"
    title = str(stage.get("title") or "").strip()
    return title or f"Stage {index}"


def now_utc() -> datetime:
    return datetime.now(UTC)


def parse_json(value: Any, default: Any) -> Any:
    if value in (None, "", "null"):
        return default
    if isinstance(value, (dict, list)):
        return value
    try:
        return json.loads(value)
    except Exception:
        return default


def dt_iso(value: Any) -> str | None:
    if not value:
        return None
    if isinstance(value, str):
        return value
    try:
        return value.isoformat()
    except Exception:
        return str(value)


def evidence_url(storage: EvidenceStorageService | None, raw_key: str | None) -> str | None:
    if not raw_key:
        return None
    if str(raw_key).startswith("data:") or str(raw_key).startswith("http"):
        return raw_key
    if str(raw_key).startswith("local://"):
        return local_evidence_public_url(str(raw_key))
    return storage.generate_presigned_url(raw_key) if storage else None


def serialize_application_documents(db: Session, application_id: int) -> list[dict[str, Any]]:
    rows = (
        db.query(ApplicationDocument)
        .filter(ApplicationDocument.application_id == application_id)
        .order_by(ApplicationDocument.uploaded_at.asc(), ApplicationDocument.id.asc())
        .all()
    )
    storage = None
    try:
        storage = EvidenceStorageService(get_s3_manager(), db)
    except Exception:
        storage = None
    return [
        {
            "id": row.id,
            "document_type": row.document_type,
            "filename": row.original_filename,
            "mime_type": row.mime_type,
            "file_size_bytes": row.file_size_bytes,
            "storage_key": row.s3_key,
            "storage_url": evidence_url(storage, row.s3_key),
            "download_url": evidence_url(storage, row.s3_key),
            "extracted_text": row.extracted_text,
            "uploaded_at": dt_iso(row.uploaded_at),
        }
        for row in rows
    ]


def serialize_verification_documents(db: Session, verification_case_id: int | None) -> list[dict[str, Any]]:
    if not verification_case_id:
        return []
    rows = (
        db.query(VerificationDocument)
        .filter(VerificationDocument.verification_case_id == verification_case_id)
        .order_by(VerificationDocument.uploaded_at.asc(), VerificationDocument.id.asc())
        .all()
    )
    storage = None
    try:
        storage = EvidenceStorageService(get_s3_manager(), db)
    except Exception:
        storage = None
    return [
        {
            "id": row.id,
            "document_type": row.document_type,
            "required": bool(row.required),
            "category": row.category,
            "filename": row.original_filename,
            "mime_type": row.mime_type,
            "file_size_bytes": row.file_size_bytes,
            "storage_key": row.s3_key,
            "storage_url": evidence_url(storage, row.s3_key),
            "download_url": evidence_url(storage, row.s3_key),
            "ocr_status": row.ocr_status,
            "ocr_fields": parse_json(row.ocr_json, {}).get("fields", {}),
            "ocr_method": parse_json(row.ocr_json, {}).get("ocr_method", ""),
            "verification_status": row.verification_status,
            "uploaded_at": dt_iso(row.uploaded_at),
            "ocr_text": row.ocr_text,
        }
        for row in rows
    ]


def human_status(value: str | None) -> str:
    if not value:
        return "Pending"
    return str(value).replace("_", " ").title()


def compact_workflow_payload(value: Any) -> Any:
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            media_flag = WORKFLOW_INLINE_MEDIA_FLAGS.get(str(key))
            if media_flag:
                cleaned[media_flag] = bool(item)
                continue
            cleaned[str(key)] = compact_workflow_payload(item)
        return cleaned
    if isinstance(value, list):
        return [compact_workflow_payload(item) for item in value]
    if isinstance(value, str):
        if value.startswith("data:image/"):
            return "[inline evidence omitted]"
        if len(value) > WORKFLOW_STRING_PREVIEW_LIMIT:
            return f"{value[:WORKFLOW_STRING_PREVIEW_LIMIT]}..."
    return value


def recent_media_preview(items: list[dict[str, Any]], *, limit: int = WORKFLOW_MEDIA_PREVIEW_LIMIT) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    total = len(items)
    preview = items[-limit:] if total > limit else items
    return preview, {
        "shown": len(preview),
        "total": total,
        "truncated": total > limit,
    }


def empty_media_summary() -> dict[str, dict[str, Any]]:
    return {
        key: {"shown": 0, "total": 0, "truncated": False}
        for key in WORKFLOW_MEDIA_SUMMARY_KEYS
    }


def empty_stage_evidence() -> dict[str, Any]:
    return {
        "room_scans": [],
        "webcam_snapshots": [],
        "screen_snapshots": [],
        "meet_snapshots": [],
        "device_info": [],
        "suspicious_events": [],
        "ai_alerts": [],
        "malpractice_incidents": [],
        "agent_decisions": [],
        "reconnect_logs": [],
        "media_summary": empty_media_summary(),
    }


def merge_stage_evidence(target: dict[str, Any], source: dict[str, Any] | None) -> dict[str, Any]:
    source = source or {}
    for key, value in target.items():
        if key == "media_summary":
            continue
        if isinstance(value, list):
            value.extend(source.get(key) or [])

    source_summary = source.get("media_summary") or {}
    for media_key in WORKFLOW_MEDIA_SUMMARY_KEYS:
        summary = target["media_summary"][media_key]
        incoming = source_summary.get(media_key) or {}
        fallback_count = len(source.get(media_key) or [])
        summary["shown"] += int(incoming.get("shown") or fallback_count)
        summary["total"] += int(incoming.get("total") or fallback_count)
        summary["truncated"] = bool(summary["truncated"] or incoming.get("truncated"))

    return target


def workflow_stage_config(rounds_raw: str | None) -> list[dict[str, Any]]:
    if not rounds_raw or not str(rounds_raw).strip():
        return []

    text = str(rounds_raw).strip()
    try:
        parsed = json.loads(text)
    except Exception:
        parsed = None

    if isinstance(parsed, dict) and parsed.get("version") == 2 and isinstance(parsed.get("stages"), list):
        stages = []
        for idx, stage in enumerate(parsed.get("stages") or [], start=1):
            rounds = []
            for round_item in stage.get("rounds") or []:
                label = (round_item.get("type") or round_item.get("round_type") or "").strip()
                if not label:
                    continue
                normalized_label = label.lower()
                rounds.append({
                    "label": label,
                    "system_type": UI_TO_SYSTEM.get(normalized_label, ""),
                    "display_only": normalized_label in DISPLAY_ONLY_ROUND_LABELS,
                })
            stages.append({
                "key": f"configured_stage_{idx}",
                "title": stage.get("name") or f"Stage {idx}",
                "is_final_hr": bool(stage.get("is_final_hr") or stage.get("isFinalHr")),
                "rounds": rounds,
            })
        return stages

    if isinstance(parsed, dict):
        ordered: list[dict[str, Any]] = []
        if parsed.get("shortlisting_test", {}).get("enabled"):
            shortlist_type = (parsed.get("shortlisting_test", {}).get("type") or "mcq").strip().lower()
            ordered.append({
                "key": "configured_stage_1",
                "title": "Stage 1",
                "is_final_hr": False,
                "rounds": [{
                    "label": "Aptitude Test" if shortlist_type == "aptitude" else "MCQ Test",
                    "system_type": "aptitude" if shortlist_type == "aptitude" else "mcq",
                    "display_only": False,
                }],
            })
        coding_rounds = []
        legacy_coding_map = {
            "coding": "Coding",
            "oop_concepts": "OOP Concepts",
            "database_design": "Database Design",
            "api_design": "API Design",
            "vibe_coding": "Vibe Coding",
        }
        for item in parsed.get("coding_round", {}).get("types", []):
            if item in legacy_coding_map:
                coding_rounds.append({"label": legacy_coding_map[item], "system_type": item})
        if coding_rounds:
            ordered.append({
                "key": f"configured_stage_{len(ordered) + 1}",
                "title": f"Stage {len(ordered) + 1}",
                "is_final_hr": False,
                "rounds": coding_rounds,
            })
        hr_rounds = []
        legacy_hr_map = {
            "technical_hr": "Technical HR",
            "hr_interview": "HR Interview",
        }
        for item in parsed.get("final_hr_round", {}).get("types", []):
            if item in legacy_hr_map:
                hr_rounds.append({"label": legacy_hr_map[item], "system_type": item})
        if hr_rounds:
            ordered.append({
                "key": f"configured_stage_{len(ordered) + 1}",
                "title": FINAL_HR_STAGE_NAME,
                "is_final_hr": True,
                "rounds": hr_rounds,
            })
        if ordered:
            return ordered

    if isinstance(parsed, list):
        stages = []
        for idx, item in enumerate(parsed, start=1):
            label = ""
            system_type = ""
            if isinstance(item, dict):
                label = (item.get("name") or item.get("title") or "").strip()
                raw_type = (item.get("type") or "").strip().lower()
                if raw_type == "live_hr":
                    label = label or "Technical HR"
                    system_type = "technical_hr"
                else:
                    system_type = UI_TO_SYSTEM.get(label.lower(), raw_type)
            elif isinstance(item, str):
                label = item.strip()
                system_type = UI_TO_SYSTEM.get(label.lower(), "")
            if not label:
                label = SYSTEM_TO_UI.get(system_type, f"Round {idx}")
            stages.append({
                "key": f"configured_stage_{idx}",
                "title": FINAL_HR_STAGE_NAME if label in HR_LABELS else f"Stage {idx}",
                "is_final_hr": label in HR_LABELS,
                "rounds": [{
                    "label": label,
                    "system_type": system_type,
                    "display_only": label.lower() in DISPLAY_ONLY_ROUND_LABELS,
                }],
            })
        if stages:
            return stages

    labels = [part.strip() for part in text.split(",") if part.strip()]
    if not labels:
        return []
    other_rounds = []
    hr_rounds = []
    for label in labels:
        item = {
            "label": label,
            "system_type": UI_TO_SYSTEM.get(label.lower(), ""),
            "display_only": label.lower() in DISPLAY_ONLY_ROUND_LABELS,
        }
        if label in HR_LABELS:
            hr_rounds.append(item)
        else:
            other_rounds.append(item)
    stages = []
    if other_rounds:
        stages.append({
            "key": "configured_stage_1",
            "title": "Stage 1",
            "is_final_hr": False,
            "rounds": other_rounds,
        })
    if hr_rounds:
        stages.append({
            "key": f"configured_stage_{len(stages) + 1}",
            "title": FINAL_HR_STAGE_NAME,
            "is_final_hr": True,
            "rounds": hr_rounds,
        })
    return stages


def ensure_offer_workflow(db: Session, application_id: int) -> OfferWorkflow:
    offer = db.query(OfferWorkflow).filter(OfferWorkflow.application_id == application_id).first()
    if offer:
        return offer
    offer = OfferWorkflow(
        application_id=application_id,
        token=uuid.uuid4().hex[:24],
        candidate_portal_expires_at=now_utc() + timedelta(days=7),
        status="joining_pending",
    )
    db.add(offer)
    db.commit()
    db.refresh(offer)
    return offer


def log_workflow_event(
    db: Session,
    *,
    application_id: int,
    event_type: str,
    summary: str,
    stage_key: str = "",
    actor_type: str = "system",
    actor_email: str = "",
    detail: dict[str, Any] | None = None,
) -> WorkflowAuditLog:
    entry = WorkflowAuditLog(
        application_id=application_id,
        stage_key=stage_key,
        event_type=event_type,
        actor_type=actor_type,
        actor_email=actor_email,
        summary=summary,
        detail_json=json.dumps(detail or {}),
    )
    db.add(entry)
    db.commit()
    db.refresh(entry)
    return entry


def delete_assessment_items(
    db: Session,
    *,
    application_id: int,
    source_session_type: str,
    source_session_id: int | None,
) -> None:
    if source_session_id is None:
        return
    (
        db.query(AssessmentItemResult)
        .filter(
            AssessmentItemResult.application_id == application_id,
            AssessmentItemResult.source_session_type == source_session_type,
            AssessmentItemResult.source_session_id == source_session_id,
        )
        .delete(synchronize_session=False)
    )
    db.commit()


def replace_assessment_items(
    db: Session,
    *,
    application_id: int,
    stage_key: str,
    source_session_type: str,
    source_session_id: int | None,
    session_token: str | None,
    items: list[dict[str, Any]],
) -> None:
    delete_assessment_items(
        db,
        application_id=application_id,
        source_session_type=source_session_type,
        source_session_id=source_session_id,
    )
    rows = []
    for idx, item in enumerate(items, start=1):
        rows.append(
            AssessmentItemResult(
                application_id=application_id,
                stage_key=stage_key,
                source_session_type=source_session_type,
                source_session_id=source_session_id,
                session_token=session_token,
                item_type=item.get("item_type", "question"),
                item_key=str(item.get("item_key", idx)),
                item_order=idx,
                question_text=item.get("question_text", ""),
                candidate_answer=item.get("candidate_answer", ""),
                correct_answer=item.get("correct_answer", ""),
                ai_summary=item.get("ai_summary", ""),
                manual_comments=item.get("manual_comments", ""),
                marks_awarded=item.get("marks_awarded"),
                marks_reason=item.get("marks_reason", ""),
                strengths_json=json.dumps(item.get("strengths", [])),
                weaknesses_json=json.dumps(item.get("weaknesses", [])),
                confidence_analysis=item.get("confidence_analysis", ""),
                technical_analysis=item.get("technical_analysis", ""),
                time_spent_seconds=item.get("time_spent_seconds"),
                started_at=item.get("started_at"),
                ended_at=item.get("ended_at"),
                total_duration_seconds=item.get("total_duration_seconds"),
                response_latency_seconds=item.get("response_latency_seconds"),
                meta_json=json.dumps(item.get("meta", {})),
            )
        )
    if rows:
        db.add_all(rows)
        db.commit()


def build_shortlist_items(test: TestSession, telemetry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    telemetry = telemetry or {}
    metrics = {
        int(item.get("question_index", idx)): item
        for idx, item in enumerate(telemetry.get("question_metrics", []), start=1)
        if isinstance(item, dict)
    }
    questions = parse_json(test.questions_json, [])
    answers = parse_json(test.answers_json, [])
    results = []
    for idx, question in enumerate(questions, start=1):
        selected_index = None
        if idx - 1 < len(answers):
            selected_index = answers[idx - 1]
        metric = metrics.get(idx, {})
        correct_index = question.get("correct")
        candidate_answer = ""
        if selected_index is not None and isinstance(question.get("options"), list):
            try:
                candidate_answer = str(question["options"][int(selected_index)])
            except Exception:
                candidate_answer = str(selected_index)
        correct_answer = ""
        if isinstance(question.get("options"), list) and correct_index is not None:
            try:
                correct_answer = str(question["options"][int(correct_index)])
            except Exception:
                correct_answer = str(correct_index)
        is_correct = selected_index is not None and correct_index is not None and int(selected_index) == int(correct_index)
        results.append({
            "item_type": "question",
            "item_key": idx,
            "question_text": question.get("question", ""),
            "candidate_answer": candidate_answer,
            "correct_answer": correct_answer,
            "marks_awarded": 1.0 if is_correct else 0.0,
            "marks_reason": "Correct answer selected." if is_correct else "Incorrect answer selected.",
            "strengths": [question.get("skill")] if is_correct and question.get("skill") else [],
            "weaknesses": [question.get("skill")] if not is_correct and question.get("skill") else [],
            "technical_analysis": question.get("explanation", ""),
            "time_spent_seconds": metric.get("time_spent_seconds"),
            "response_latency_seconds": metric.get("response_latency_seconds"),
            "meta": {
                "options": question.get("options", []),
                "skill": question.get("skill", ""),
                "difficulty": question.get("difficulty", ""),
                "question_index": idx,
                "authenticity_trap": bool(question.get("authenticity_trap")),
                "assessment_kind": test.assessment_kind or "mcq",
            },
            "started_at": _dt_from_any(metric.get("started_at")),
            "ended_at": _dt_from_any(metric.get("ended_at")),
            "total_duration_seconds": metric.get("time_spent_seconds"),
        })
    return results


def build_coding_items(session: CodingSession, telemetry: dict[str, Any] | None = None) -> list[dict[str, Any]]:
    telemetry = telemetry or {}
    results = []
    if session.round_type in {"coding", "vibe"}:
        problems = parse_json(session.problems_json, [])
        submissions = parse_json(session.submissions_json, [])
        metrics = {}
        for idx, item in enumerate(telemetry.get("problem_metrics", []), start=1):
            if not isinstance(item, dict):
                continue
            metric_key = item.get("problem_id")
            if metric_key in (None, ""):
                metric_key = item.get("problem_index", idx)
            metrics[str(metric_key)] = item
        submission_by_id = {}
        for idx, item in enumerate(submissions, start=1):
            if not isinstance(item, dict):
                continue
            submission_key = item.get("problem_id")
            if submission_key in (None, ""):
                if item.get("problem_idx") is not None:
                    submission_key = int(item.get("problem_idx")) + 1
                else:
                    submission_key = idx
            submission_by_id[str(submission_key)] = item
        for idx, problem in enumerate(problems, start=1):
            key = str(problem.get("id", idx))
            submission = submission_by_id.get(key, {})
            metric = metrics.get(key, {})
            code = submission.get("code") or submission.get("answer") or ""
            all_files = submission.get("files") or []
            code_len = len(str(code).strip())
            score = 1.0 if code_len >= 12 else 0.0
            proctoring_summary = parse_json(session.proctoring_json, {})
            results.append({
                "item_type": "vibe_submission" if session.round_type == "vibe" else "coding_problem",
                "item_key": key,
                "question_text": problem.get("title", ""),
                "candidate_answer": str(code),
                "correct_answer": "Manual/code review required",
                "ai_summary": proctoring_summary.get("feedback") or proctoring_summary.get("trap_summary", ""),
                "marks_awarded": session.score_pct if session.round_type == "vibe" else score,
                "marks_reason": (
                    proctoring_summary.get("reasoning")
                    or ("Non-empty code submission captured." if score else "Submission missing or too short.")
                ),
                "strengths": [problem.get("difficulty")] if score else [],
                "weaknesses": [] if score else [problem.get("difficulty")],
                "confidence_analysis": metric.get("confidence_analysis", ""),
                "technical_analysis": problem.get("description", ""),
                "time_spent_seconds": metric.get("time_spent_seconds"),
                "response_latency_seconds": metric.get("response_latency_seconds"),
                "meta": {
                    "language": submission.get("language", ""),
                    "problem_id": key,
                    "difficulty": problem.get("difficulty", ""),
                    "examples": problem.get("examples", []),
                    "languages": problem.get("languages", []),
                    "files": all_files,
                },
                "started_at": _dt_from_any(metric.get("started_at")),
                "ended_at": _dt_from_any(metric.get("ended_at")),
                "total_duration_seconds": metric.get("total_duration_seconds") or metric.get("time_spent_seconds"),
            })
    else:
        questions = parse_json(session.questions_json, [])
        answers = parse_json(session.answers_json, {})
        metrics = {
            str(item.get("question_id", idx)): item
            for idx, item in enumerate(telemetry.get("question_metrics", []), start=1)
            if isinstance(item, dict)
        }
        for idx, question in enumerate(questions, start=1):
            key = str(question.get("id", idx))
            answer = answers.get(key, answers.get(str(idx - 1), answers.get(idx - 1)))
            metric = metrics.get(key, {})
            correct_index = question.get("correct_index")
            candidate_answer = ""
            if answer is not None and isinstance(question.get("options"), list):
                try:
                    candidate_answer = str(question["options"][int(answer)])
                except Exception:
                    candidate_answer = str(answer)
            correct_answer = ""
            if isinstance(question.get("options"), list) and correct_index is not None:
                try:
                    correct_answer = str(question["options"][int(correct_index)])
                except Exception:
                    correct_answer = str(correct_index)
            is_correct = answer is not None and correct_index is not None and int(answer) == int(correct_index)
            results.append({
                "item_type": "question",
                "item_key": key,
                "question_text": question.get("question", ""),
                "candidate_answer": candidate_answer,
                "correct_answer": correct_answer,
                "marks_awarded": 1.0 if is_correct else 0.0,
                "marks_reason": "Correct answer selected." if is_correct else "Incorrect answer selected.",
                "strengths": [session.round_type] if is_correct else [],
                "weaknesses": [session.round_type] if not is_correct else [],
                "technical_analysis": "",
                "time_spent_seconds": metric.get("time_spent_seconds"),
                "response_latency_seconds": metric.get("response_latency_seconds"),
                "meta": {
                    "options": question.get("options", []),
                    "question_id": key,
                    "is_trap": bool(question.get("is_trap")),
                },
                "started_at": _dt_from_any(metric.get("started_at")),
                "ended_at": _dt_from_any(metric.get("ended_at")),
                "total_duration_seconds": metric.get("time_spent_seconds"),
            })
    return results


def _dt_from_any(value: Any) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except Exception:
            return None
    return None


def infer_round_system_type(obj: Any) -> str:
    if isinstance(obj, TestSession):
        return "mcq"
    if isinstance(obj, CodingSession):
        return {
            "coding": "coding",
            "oop": "oop_concepts",
            "database": "database_design",
            "api": "api_design",
            "vibe": "vibe_coding",
        }.get(obj.round_type or "coding", "coding")
    if isinstance(obj, LiveSession):
        return "hr_interview" if obj.interview_type == "hr_interview" else "technical_hr"
    return ""


def latest_assessment_items(
    db: Session,
    *,
    application_id: int,
    source_session_type: str,
    source_session_id: int | None,
    fallback_items: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if source_session_id is None:
        return fallback_items
    rows = (
        db.query(AssessmentItemResult)
        .filter(
            AssessmentItemResult.application_id == application_id,
            AssessmentItemResult.source_session_type == source_session_type,
            AssessmentItemResult.source_session_id == source_session_id,
        )
        .order_by(AssessmentItemResult.item_order.asc(), AssessmentItemResult.id.asc())
        .all()
    )
    if not rows:
        return fallback_items
    return [
        {
            "item_type": row.item_type,
            "item_key": row.item_key,
            "question_text": row.question_text,
            "candidate_answer": row.candidate_answer,
            "correct_answer": row.correct_answer,
            "ai_summary": row.ai_summary,
            "manual_comments": row.manual_comments,
            "marks_awarded": row.marks_awarded,
            "marks_reason": row.marks_reason,
            "strengths": parse_json(row.strengths_json, []),
            "weaknesses": parse_json(row.weaknesses_json, []),
            "confidence_analysis": row.confidence_analysis,
            "technical_analysis": row.technical_analysis,
            "time_spent_seconds": row.time_spent_seconds,
            "started_at": dt_iso(row.started_at),
            "ended_at": dt_iso(row.ended_at),
            "total_duration_seconds": row.total_duration_seconds,
            "response_latency_seconds": row.response_latency_seconds,
            "meta": parse_json(row.meta_json, {}),
        }
        for row in rows
    ]


def collect_stage_evidence(db: Session, session_token: str | None) -> dict[str, Any]:
    if not session_token:
        return empty_stage_evidence()

    proctoring_rows = (
        db.query(ProctoringEvidence)
        .filter(ProctoringEvidence.session_token == session_token)
        .order_by(ProctoringEvidence.created_at.asc(), ProctoringEvidence.id.asc())
        .all()
    )
    room_scans = (
        db.query(RoomScan)
        .filter(RoomScan.session_token == session_token)
        .order_by(RoomScan.created_at.asc(), RoomScan.id.asc())
        .all()
    )
    incidents = (
        db.query(MalpracticeIncident)
        .filter(MalpracticeIncident.session_token == session_token)
        .order_by(MalpracticeIncident.created_at.asc(), MalpracticeIncident.id.asc())
        .all()
    )
    decisions = (
        db.query(AgentDecisionLog)
        .filter(AgentDecisionLog.session_token == session_token)
        .order_by(AgentDecisionLog.created_at.asc(), AgentDecisionLog.id.asc())
        .all()
    )
    reconnects = (
        db.query(ReconnectLog)
        .filter(ReconnectLog.session_token == session_token)
        .order_by(ReconnectLog.created_at.asc(), ReconnectLog.id.asc())
        .all()
    )

    storage = None
    try:
        storage = EvidenceStorageService(get_s3_manager(), db)
    except Exception:
        storage = None

    suspicious_events = []
    webcam_snapshots = []
    screen_snapshots = []
    meet_snapshots = []
    device_info = []
    ai_alerts = []
    for row in proctoring_rows:
        raw_payload = parse_json(row.evidence_json, {})
        payload = compact_workflow_payload(raw_payload)
        event = {
            "event_type": row.event_type,
            "severity": row.severity,
            "risk_delta": row.risk_delta,
            "timestamp": dt_iso(row.created_at),
            "payload": payload,
        }
        suspicious_events.append(event)
        face_image = evidence_url(storage, raw_payload.get("face_storage_key")) or raw_payload.get("face_b64")
        screen_image = evidence_url(storage, raw_payload.get("screen_storage_key")) or raw_payload.get("screen_b64")
        meet_image = evidence_url(storage, raw_payload.get("snapshot_storage_key")) or raw_payload.get("snapshot_b64")
        if face_image:
            webcam_snapshots.append({
                "timestamp": dt_iso(row.created_at),
                "event_type": row.event_type,
                "image_b64": face_image,
                "face_similarity": raw_payload.get("face_similarity"),
            })
        if screen_image:
            screen_snapshots.append({
                "timestamp": dt_iso(row.created_at),
                "event_type": row.event_type,
                "image_b64": screen_image,
            })
        if meet_image:
            meet_snapshots.append({
                "timestamp": dt_iso(row.created_at),
                "event_type": row.event_type,
                "image_b64": meet_image,
            })
        if row.event_type in {"device_info", "device_fingerprint", "session_opened"}:
            device_info.append({
                "timestamp": dt_iso(row.created_at),
                "event_type": row.event_type,
                "payload": payload,
            })
        if row.event_type in {"face_mismatch", "manual_flag", "meet_alert"} or raw_payload.get("alert"):
            ai_alerts.append({
                "timestamp": dt_iso(row.created_at),
                "event_type": row.event_type,
                "severity": row.severity,
                "message": raw_payload.get("alert") or raw_payload.get("reason") or row.event_type,
            })

    room_scan_entries = []
    for scan in room_scans:
        frames = (
            db.query(RoomScanFrame, EvidenceFile)
            .join(EvidenceFile, EvidenceFile.id == RoomScanFrame.evidence_file_id)
            .filter(RoomScanFrame.room_scan_id == scan.id)
            .order_by(RoomScanFrame.frame_index.asc(), RoomScanFrame.id.asc())
            .all()
        )
        room_scan_entries.append({
            "scan_id": scan.id,
            "scan_type": scan.scan_type,
            "scan_status": scan.scan_status,
            "verdict": scan.verdict,
            "suspicious_items": parse_json(scan.suspicious_items_json, []),
            "created_at": dt_iso(scan.created_at),
            "completed_at": dt_iso(scan.completed_at),
            "frames": [
                {
                    "frame_index": room_frame.frame_index,
                    "has_violation": room_frame.has_violation,
                    "s3_key": evidence.s3_key,
                    "mime_type": evidence.mime_type,
                    "url": evidence_url(storage, evidence.s3_key),
                }
                for room_frame, evidence in frames
            ],
        })

    incident_entries = []
    for incident in incidents:
        links = (
            db.query(IncidentEvidence, EvidenceFile)
            .join(EvidenceFile, EvidenceFile.id == IncidentEvidence.evidence_file_id)
            .filter(IncidentEvidence.incident_id == incident.id)
            .order_by(IncidentEvidence.sequence_order.asc(), IncidentEvidence.id.asc())
            .all()
        )
        incident_entries.append({
            "incident_id": incident.id,
            "question_id": incident.question_id,
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "confidence_score": incident.confidence_score,
            "agent_name": incident.agent_name,
            "reason_text": incident.reason_text,
            "created_at": dt_iso(incident.created_at),
            "evidence_files": [
                {
                    "type": evidence.evidence_type,
                    "mime_type": evidence.mime_type,
                    "url": evidence_url(storage, evidence.s3_key),
                    "s3_key": evidence.s3_key,
                }
                for _, evidence in links
            ],
        })

    webcam_preview, webcam_summary = recent_media_preview(webcam_snapshots)
    screen_preview, screen_summary = recent_media_preview(screen_snapshots)
    meet_preview, meet_summary = recent_media_preview(meet_snapshots)

    return {
        "room_scans": room_scan_entries,
        "webcam_snapshots": webcam_preview,
        "screen_snapshots": screen_preview,
        "meet_snapshots": meet_preview,
        "device_info": device_info,
        "suspicious_events": suspicious_events,
        "ai_alerts": ai_alerts,
        "malpractice_incidents": incident_entries,
        "media_summary": {
            "webcam_snapshots": webcam_summary,
            "screen_snapshots": screen_summary,
            "meet_snapshots": meet_summary,
        },
        "agent_decisions": [
            {
                "agent_name": row.agent_name,
                "detection_type": row.detection_type,
                "confidence_score": row.confidence_score,
                "reasoning_text": row.reasoning_text,
                "processing_time_ms": row.processing_time_ms,
                "created_at": dt_iso(row.created_at),
            }
            for row in decisions
        ],
        "reconnect_logs": [
            {
                "gap_duration_seconds": row.gap_duration_seconds,
                "fingerprint_match": row.fingerprint_match,
                "disconnect_verdict": row.disconnect_verdict,
                "gap_video_verdict": row.gap_video_verdict,
                "combined_verdict": row.combined_verdict,
                "risk_penalty": row.risk_penalty,
                "analysis_completed": row.analysis_completed,
                "created_at": dt_iso(row.created_at),
            }
            for row in reconnects
        ],
    }


def enrich_stage_evidence(
    evidence: dict[str, Any],
    *,
    fallback_face_b64: str | None = None,
) -> dict[str, Any]:
    next_evidence = dict(evidence or {})
    webcam = list(next_evidence.get("webcam_snapshots") or [])
    if not webcam and fallback_face_b64:
        webcam.append({
            "timestamp": None,
            "event_type": "verification_face",
            "image_b64": fallback_face_b64,
            "face_similarity": None,
        })
    next_evidence["webcam_snapshots"] = webcam
    return next_evidence


def _round_status(round_data: dict[str, Any]) -> tuple[str, str]:
    if round_data.get("failed"):
        return "rejected", round_data.get("status_label") or "Rejected"
    if round_data.get("completed"):
        if round_data.get("selected"):
            return "selected", round_data.get("status_label") or "Selected"
        return "completed", round_data.get("status_label") or "Completed"
    if round_data.get("available"):
        return "in_progress", round_data.get("status_label") or "In Progress"
    return "pending", round_data.get("status_label") or "Pending"


def build_workflow_payload(db: Session, application: Application, job: Any) -> dict[str, Any]:
    configured_stages = workflow_stage_config(getattr(job, "rounds", None))
    shortlist_tests = (
        db.query(TestSession)
        .filter(TestSession.application_id == application.id)
        .order_by(TestSession.created_at.desc(), TestSession.id.desc())
        .all()
    )
    coding_rounds = (
        db.query(CodingSession)
        .filter(CodingSession.application_id == application.id)
        .order_by(CodingSession.created_at.desc(), CodingSession.id.desc())
        .all()
    )
    live_sessions = (
        db.query(LiveSession)
        .filter(LiveSession.application_id == application.id)
        .order_by(LiveSession.created_at.desc(), LiveSession.id.desc())
        .all()
    )
    verification_case = (
        db.query(VerificationCase)
        .filter(VerificationCase.application_id == application.id)
        .order_by(VerificationCase.created_at.desc(), VerificationCase.id.desc())
        .first()
    )
    application_documents = serialize_application_documents(db, application.id)
    verification_documents = serialize_verification_documents(db, verification_case.id if verification_case else None)
    offer = db.query(OfferWorkflow).filter(OfferWorkflow.application_id == application.id).first()
    audit_log = (
        db.query(WorkflowAuditLog)
        .filter(WorkflowAuditLog.application_id == application.id)
        .order_by(WorkflowAuditLog.created_at.desc(), WorkflowAuditLog.id.desc())
        .all()
    )

    round_lookup: dict[str, list[dict[str, Any]]] = {key: [] for key in SYSTEM_TO_UI}

    for test in shortlist_tests:
        assessment_kind = (test.assessment_kind or "mcq").strip().lower()
        fallback_items = build_shortlist_items(test)
        items = latest_assessment_items(
            db,
            application_id=application.id,
            source_session_type="shortlisting",
            source_session_id=test.id,
            fallback_items=fallback_items,
        )
        round_lookup.setdefault(assessment_kind, []).append({
            "label": SYSTEM_TO_UI.get(assessment_kind, "Shortlisting Test"),
            "status": test.status,
            "status_label": human_status(test.status),
            "completed": test.status == "submitted",
            "available": True,
            "failed": test.passed is False,
            "selected": False,
            "score_pct": test.score_pct,
            "pass_score": test.pass_score,
            "passed": test.passed,
            "summary": parse_json(test.proctoring_json, {}).get("summary") or "",
            "ai_summary": parse_json(test.proctoring_json, {}).get("summary") or "",
            "manual_comments": "",
            "session_token": test.token,
            "manual_round_url": settings.public_frontend_path(f"/test/{test.token}"),
            "email_sent": bool(test.email_sent),
            "assessment_kind": assessment_kind,
            "items": items,
            "evidence": enrich_stage_evidence(
                collect_stage_evidence(db, test.token),
                fallback_face_b64=test.verification_face_b64,
            ),
            "created_at": dt_iso(test.created_at),
            "submitted_at": dt_iso(test.submitted_at),
            "risk_score": test.risk_score,
            "proctoring_risk": test.proctoring_risk,
            "block_reason": test.block_reason,
            "face_continuity_score": test.face_continuity_score,
            "attempt_id": test.id,
        })

    for session in coding_rounds:
        system_type = infer_round_system_type(session)
        fallback_items = build_coding_items(session)
        items = latest_assessment_items(
            db,
            application_id=application.id,
            source_session_type="coding",
            source_session_id=session.id,
            fallback_items=fallback_items,
        )
        round_lookup.setdefault(system_type, []).append({
            "label": SYSTEM_TO_UI.get(system_type, session.round_type or "Assessment"),
            "status": session.status,
            "status_label": human_status(session.status),
            "completed": session.status == "submitted",
            "available": True,
            "failed": session.passed is False,
            "selected": False,
            "score_pct": session.score_pct,
            "pass_score": session.pass_score,
            "passed": session.passed,
            "summary": parse_json(session.proctoring_json, {}).get("summary") or "",
            "ai_summary": parse_json(session.proctoring_json, {}).get("summary") or "",
            "manual_comments": "",
            "session_token": session.token,
            "manual_round_url": settings.public_frontend_path(f"/coding/{session.token}"),
            "email_sent": bool(session.email_sent),
            "items": items,
            "evidence": enrich_stage_evidence(
                collect_stage_evidence(db, session.token),
                fallback_face_b64=session.verification_face_b64,
            ),
            "created_at": dt_iso(session.created_at),
            "submitted_at": dt_iso(session.submitted_at),
            "risk_score": session.risk_score,
            "proctoring_risk": session.proctoring_risk,
            "block_reason": session.block_reason,
            "face_continuity_score": session.face_continuity_score,
            "authenticity_score": session.authenticity_score,
            "attempt_id": session.id,
        })

    for live in live_sessions:
        system_type = infer_round_system_type(live)
        transcript_lines = [line for line in (live.transcript or "").split("\n") if line.strip()]
        qa_pairs = []
        pending_question = None
        for line in transcript_lines:
            lower = line.lower()
            if "[hr]" in lower:
                pending_question = line.split("]", 2)[-1].strip()
            elif "[candidate]" in lower and pending_question:
                qa_pairs.append({
                    "item_type": "interview_exchange",
                    "item_key": len(qa_pairs) + 1,
                    "question_text": pending_question,
                    "candidate_answer": line.split("]", 2)[-1].strip(),
                    "correct_answer": "Manual interview evaluation",
                    "ai_summary": live.ai_reason or "",
                    "manual_comments": live.manual_reason or "",
                    "marks_awarded": None,
                    "marks_reason": live.final_summary or "",
                    "strengths": [],
                    "weaknesses": [],
                    "confidence_analysis": "",
                    "technical_analysis": "",
                    "meta": {},
                })
                pending_question = None
        items = latest_assessment_items(
            db,
            application_id=application.id,
            source_session_type="live_hr",
            source_session_id=live.id,
            fallback_items=qa_pairs,
        )
        ai_scores = parse_json(live.ai_score_json or live.candidate_score, {})
        manual_scores = parse_json(live.manual_score_json, {})
        average_score = None
        score_values = [float(v) for v in manual_scores.values() if isinstance(v, (int, float, str)) and str(v).strip()]
        if not score_values:
            score_values = [float(v) for v in ai_scores.values() if isinstance(v, (int, float, str)) and str(v).strip()]
        if score_values:
            average_score = round(sum(score_values) / len(score_values), 2)
        round_lookup.setdefault(system_type, []).append({
            "label": SYSTEM_TO_UI.get(system_type, "Live Interview"),
            "status": live.status,
            "status_label": "Ended" if live.status == "ended" else human_status(live.status),
            "completed": live.status == "ended",
            "available": True,
            "failed": live.outcome in {"fail", "reject", "rejected"},
            "selected": live.outcome in {"pass", "selected"},
            "score_pct": average_score,
            "pass_score": 7,
            "passed": live.outcome in {"pass", "selected"},
            "summary": live.final_summary or live.manual_reason or live.ai_reason or "",
            "ai_summary": live.ai_reason or "",
            "manual_comments": live.manual_reason or "",
            "session_token": live.token,
            "manual_round_url": settings.public_frontend_path(f"/livehr/{live.token}"),
            "email_sent": False,
            "items": items,
            "evidence": collect_stage_evidence(db, live.token),
            "created_at": dt_iso(live.created_at),
            "submitted_at": dt_iso(live.started_at),
            "risk_score": None,
            "proctoring_risk": None,
            "block_reason": "",
            "face_continuity_score": None,
            "attempt_id": live.id,
            "transcript": transcript_lines,
            "ai_flags": parse_json(live.ai_flags_json, []),
            "ai_scorecard": ai_scores,
            "manual_scorecard": manual_scores,
        })

    stages: list[dict[str, Any]] = []
    eval_payload = parse_json(application.eval_data, {})
    recommendation = application.eval_recommendation or eval_payload.get("hiring_recommendation") or ""
    eval_score = None
    try:
        eval_score = float(application.eval_score) if application.eval_score not in (None, "") else None
    except Exception:
        eval_score = None
    stages.append({
        "key": "application_review",
        "title": "Stage 0 — Application Review",
        "kind": "application_review",
        "order": 0,
        "primary_status": "completed",
        "secondary_status": recommendation or "Applied",
        "summary": application.eval_summary or eval_payload.get("summary") or "Candidate application received and ready for review.",
        "score": eval_score,
        "items": [],
        "rounds": [],
        "evidence": {
            "room_scans": [],
            "webcam_snapshots": [],
            "screen_snapshots": [],
            "meet_snapshots": [],
            "device_info": [],
            "suspicious_events": [],
            "ai_alerts": [],
            "malpractice_incidents": [],
            "agent_decisions": [],
            "reconnect_logs": [],
        },
        "evaluation": eval_payload,
        "application_documents": application_documents,
        "actions": {
            "can_reject": True,
        },
    })

    stages[0]["title"] = "Stage 0 - Application Review"
    score_comparison = []
    if eval_score is not None:
        score_comparison.append({"label": "Application Review", "score": eval_score, "stage_key": "application_review"})

    for idx, configured_stage in enumerate(configured_stages, start=1):
        stage_title = normalized_stage_title(configured_stage, idx)
        round_cards = []
        flattened_items = []
        stage_evidence = empty_stage_evidence()
        round_statuses = []
        score_values = []
        for round_info in configured_stage.get("rounds", []):
            attempts = round_lookup.get(round_info.get("system_type"), [])
            latest = attempts[0] if attempts else None
            if latest:
                card = dict(latest)
                card["display_only"] = bool(round_info.get("display_only"))
            else:
                is_display_only = bool(round_info.get("display_only"))
                card = {
                    "label": round_info.get("label"),
                    "status": "pending",
                    "status_label": "Display Only" if is_display_only else "Pending",
                    "completed": False,
                    "available": (application.status in {f"round_{idx}", f"round_{idx + 1}"} or application.status in POST_INTERVIEW_STATUSES) if not is_display_only else False,
                    "failed": False,
                    "selected": False,
                    "score_pct": None,
                    "pass_score": None,
                    "passed": None,
                    "summary": "Display-only round. HR can see this in the workflow, but it does not run inside the platform." if is_display_only else "Not attempted yet.",
                    "ai_summary": "",
                    "manual_comments": "",
                    "session_token": None,
                    "items": [],
                    "evidence": collect_stage_evidence(db, None),
                    "created_at": None,
                    "submitted_at": None,
                    "attempt_id": None,
                    "display_only": is_display_only,
                }
            primary, secondary = _round_status(card)
            round_statuses.append(primary)
            if card.get("score_pct") is not None:
                score_values.append(float(card["score_pct"]))
            flattened_items.extend(card.get("items", []))
            merge_stage_evidence(stage_evidence, card.get("evidence"))
            card["primary_status"] = primary
            card["secondary_status"] = secondary
            round_cards.append(card)

        for media_key in WORKFLOW_MEDIA_SUMMARY_KEYS:
            preview, preview_summary = recent_media_preview(stage_evidence[media_key])
            merged_total = int(stage_evidence["media_summary"][media_key]["total"] or 0)
            total = max(merged_total, preview_summary["total"])
            stage_evidence[media_key] = preview
            stage_evidence["media_summary"][media_key] = {
                "shown": len(preview),
                "total": total,
                "truncated": bool(stage_evidence["media_summary"][media_key]["truncated"] or total > len(preview)),
            }

        if "rejected" in round_statuses:
            primary_status = "rejected"
            secondary_status = "Rejected"
        elif round_statuses and all(value in {"completed", "selected"} for value in round_statuses):
            primary_status = "completed"
            secondary_status = "Completed"
        elif any(value == "in_progress" for value in round_statuses):
            primary_status = "in_progress"
            secondary_status = "In Progress"
        else:
            primary_status = "pending"
            secondary_status = "Pending"

        stage_score = round(sum(score_values) / len(score_values), 2) if score_values else None
        if stage_score is not None:
            score_comparison.append({"label": stage_title, "score": stage_score, "stage_key": configured_stage["key"]})
        stages.append({
            "key": configured_stage["key"],
            "title": stage_title,
            "kind": "assessment_stage",
            "order": idx,
            "primary_status": primary_status,
            "secondary_status": secondary_status,
            "summary": next((card.get("summary") for card in round_cards if card.get("summary")), "Waiting for this stage to begin."),
            "score": stage_score,
            "items": flattened_items,
            "rounds": round_cards,
            "evidence": stage_evidence,
            "actions": {"can_reject": True},
        })

    offer = offer or None
    joining_stage_status = "completed" if offer and offer.joining_date else "in_progress" if application.status in {"joining_pending", "offer_pending", "offer_sent", "offer_signed", "approval_pending", "hired", "on_hold", "onboarding_in_progress", "onboarding_completed"} else "pending"
    joining_secondary = (
        "Completed"
        if offer and offer.joining_date
        else "In Progress"
        if joining_stage_status == "in_progress"
        else "Pending"
    )
    stages.append({
        "key": "joining_setup",
        "title": "Joining Setup",
        "kind": "joining_setup",
        "order": len(stages),
        "primary_status": joining_stage_status,
        "secondary_status": joining_secondary,
        "summary": "Capture joining date, work mode, reporting structure, compensation, and offer metadata before background verification.",
        "score": None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": _serialize_offer(offer),
        "actions": {
            "can_edit": application.status not in {"rejected", "hired"},
            "can_start_bgv": bool(offer and offer.joining_date and application.status in {"joining_pending", "bgv_pending", "bgv_review", "offer_pending", "offer_sent", "offer_signed", "approval_pending", "hired", "on_hold", "onboarding_in_progress", "onboarding_completed"}),
        },
    })

    bgv_status = "pending"
    bgv_secondary = "Pending"
    bgv_summary = "Background verification has not started yet."
    bgv_data = None
    if verification_case:
        bgv_data = {
            "id": verification_case.id,
            "token": verification_case.token,
            "status": verification_case.status,
            "typed_full_name": verification_case.typed_full_name,
            "typed_address": verification_case.typed_address,
            "typed_city": verification_case.typed_city,
            "typed_state": verification_case.typed_state,
            "typed_pincode": verification_case.typed_pincode,
            "typed_pan": verification_case.typed_pan,
            "typed_aadhaar": verification_case.typed_aadhaar,
            "review_summary": verification_case.review_summary,
            "review_reason": verification_case.review_reason,
            "mismatches": parse_json(verification_case.mismatch_json, []),
            "documents": parse_json(verification_case.documents_json, {}),
            "ocr": parse_json(verification_case.ocr_json, {}),
            "document_items": verification_documents,
            "face": parse_json(verification_case.face_json, {}),
            "submitted_at": dt_iso(verification_case.submitted_at),
            "reviewed_at": dt_iso(verification_case.reviewed_at),
            "reviewer_email": verification_case.reviewer_email,
        }
        if verification_case.status in {"accepted"}:
            bgv_status = "completed"
            bgv_secondary = "Approved"
        elif verification_case.status in {"rejected"}:
            bgv_status = "rejected"
            bgv_secondary = "Rejected"
        elif verification_case.status in {"submitted", "hold"}:
            bgv_status = "in_progress"
            bgv_secondary = human_status(verification_case.status)
        else:
            bgv_status = "pending"
            bgv_secondary = human_status(verification_case.status)
        bgv_summary = verification_case.review_summary or "Verification case created."
    stages.append({
        "key": "background_verification",
        "title": "Background Verification",
        "kind": "background_verification",
        "order": len(stages),
        "primary_status": bgv_status,
        "secondary_status": bgv_secondary,
        "summary": bgv_summary,
        "score": None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": bgv_data,
        "actions": {
            "can_review": bool(verification_case and verification_case.status in {"submitted", "hold"}),
        },
    })

    offer_stage_status = "completed" if offer and offer.offer_generated_at else "pending"
    offer_stage_secondary = "Offer Ready" if offer and offer.offer_generated_at else "Pending"
    if offer and offer.offer_sent_at and offer_stage_status != "completed":
        offer_stage_status = "in_progress"
        offer_stage_secondary = "Offer Sent"
    if offer and offer.offer_generated_at and application.status in {"offer_sent", "offer_signed", "approval_pending", "hired", "on_hold", "onboarding_in_progress", "onboarding_completed"}:
        offer_stage_status = "completed"
        offer_stage_secondary = "Offer Generated"
    stages.append({
        "key": "offer_letter",
        "title": "Offer Letter",
        "kind": "offer_letter",
        "order": len(stages),
        "primary_status": offer_stage_status,
        "secondary_status": offer_stage_secondary,
        "summary": "Generate and send the offer letter once verification is approved.",
        "score": None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": _serialize_offer(offer),
        "actions": {
            "can_generate": bool(offer and (verification_case and verification_case.status == "accepted")),
        },
    })

    candidate_stage_status = "pending"
    candidate_secondary = "Pending"
    if offer and offer.candidate_response == "rejected":
        candidate_stage_status = "rejected"
        candidate_secondary = "Rejected"
    elif offer and offer.candidate_response == "accepted":
        candidate_stage_status = "selected"
        candidate_secondary = "Signed"
    elif offer and offer.offer_sent_at:
        candidate_stage_status = "in_progress"
        candidate_secondary = "Awaiting Candidate"
    stages.append({
        "key": "candidate_acceptance",
        "title": "Candidate Acceptance & Signature",
        "kind": "candidate_acceptance",
        "order": len(stages),
        "primary_status": candidate_stage_status,
        "secondary_status": candidate_secondary,
        "summary": offer.candidate_remarks if offer and offer.candidate_remarks else "Candidate can review the offer, accept or reject, and submit a signature.",
        "score": None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": _serialize_offer(offer),
        "actions": {},
    })

    approval_status = "pending"
    approval_secondary = "Pending"
    if offer and offer.hr_final_approval_status == "approved":
        approval_status = "selected"
        approval_secondary = "Approved"
    elif offer and offer.hr_final_approval_status in {"rejected", "on_hold"}:
        approval_status = "rejected" if offer.hr_final_approval_status == "rejected" else "in_progress"
        approval_secondary = human_status(offer.hr_final_approval_status)
    elif offer and offer.candidate_response == "accepted":
        approval_status = "in_progress"
        approval_secondary = "Awaiting Approval"
    stages.append({
        "key": "hr_final_approval",
        "title": "HR Final Approval",
        "kind": "hr_final_approval",
        "order": len(stages),
        "primary_status": approval_status,
        "secondary_status": approval_secondary,
        "summary": offer.hr_final_approval_reason if offer and offer.hr_final_approval_reason else "Finalize the signed offer before the hiring outcome is published.",
        "score": None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": _serialize_offer(offer),
        "actions": {
            "can_approve": bool(offer and offer.candidate_response == "accepted"),
        },
    })

    final_status = "pending"
    final_secondary = human_status(offer.final_outcome if offer and offer.final_outcome else application.status)
    if (offer and offer.final_outcome == "hired") or application.status in {"hired", "onboarding_in_progress", "onboarding_completed"}:
        final_status = "selected"
        final_secondary = "Hired"
    elif application.status in {"rejected"}:
        final_status = "rejected"
        final_secondary = "Rejected"
    elif application.status in {"on_hold"}:
        final_status = "in_progress"
        final_secondary = "On Hold"
    elif application.status in {"offer_pending", "offer_sent", "offer_signed", "approval_pending"}:
        final_status = "in_progress"
        final_secondary = human_status(application.status)
    stages.append({
        "key": "final_hiring_outcome",
        "title": "Final Hiring Outcome",
        "kind": "final_hiring_outcome",
        "order": len(stages),
        "primary_status": final_status,
        "secondary_status": final_secondary,
        "summary": offer.final_outcome_summary if offer and offer.final_outcome_summary else "Publish the final hiring decision with HR remarks and recommendation score.",
        "score": offer.final_recommendation_score if offer else None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": _serialize_offer(offer),
        "actions": {
            "can_update": bool(offer),
        },
    })
    if offer and offer.final_recommendation_score is not None:
        score_comparison.append({"label": "Final Recommendation", "score": offer.final_recommendation_score, "stage_key": "final_hiring_outcome"})

    onboarding_status = "pending"
    onboarding_secondary = "Pending"
    if application.status == "onboarding_completed":
        onboarding_status = "completed"
        onboarding_secondary = "Completed"
    elif application.status == "onboarding_in_progress":
        onboarding_status = "in_progress"
        onboarding_secondary = "In Progress"
    elif application.status == "hired":
        onboarding_status = "in_progress"
        onboarding_secondary = "Ready"
    stages.append({
        "key": "employee_onboarding",
        "title": "Employee Onboarding",
        "kind": "employee_onboarding",
        "order": len(stages),
        "primary_status": onboarding_status,
        "secondary_status": onboarding_secondary,
        "summary": offer.onboarding_notes if offer and offer.onboarding_notes else "Track onboarding handoff and completion notes after the hiring decision is finalized.",
        "score": None,
        "items": [],
        "rounds": [],
        "evidence": collect_stage_evidence(db, None),
        "data": _serialize_offer(offer),
        "actions": {
            "can_update": bool(offer and application.status in {"hired", "onboarding_in_progress", "onboarding_completed"}),
        },
    })

    return {
        "candidate": {
            "id": application.id,
            "full_name": application.full_name,
            "email": application.email,
            "phone": application.phone,
            "location": application.location,
            "current_title": application.current_title,
            "company_name": application.company_name,
            "years_exp": application.years_exp,
            "current_lpa": application.current_lpa,
            "notice_period": application.notice_period,
            "technical_skills": application.technical_skills,
            "soft_skills": application.soft_skills,
            "cover_letter": application.cover_letter,
            "linkedin_url": application.linkedin_url,
            "github_url": application.github_url,
            "leetcode_url": application.leetcode_url,
            "portfolio_url": application.portfolio_url,
            "degree_type": application.degree_type,
            "field_of_study": application.field_of_study,
            "institution": application.institution,
            "submitted_at": dt_iso(application.submitted_at),
            "application_documents": application_documents,
        },
        "application": {
            "id": application.id,
            "status": application.status,
            "eval_score": application.eval_score,
            "eval_recommendation": application.eval_recommendation,
            "eval_summary": application.eval_summary,
        },
        "job": {
            "id": getattr(job, "id", None),
            "job_name": getattr(job, "job_name", ""),
            "rounds": getattr(job, "rounds", ""),
            "department": getattr(job, "department", ""),
            "job_type": getattr(job, "job_type", ""),
        },
        "stages": stages,
        "score_comparison": score_comparison,
        "final_decision": {
            "application_status": application.status,
            "final_outcome": offer.final_outcome if offer else "",
            "summary": offer.final_outcome_summary if offer else "",
            "recommendation_score": offer.final_recommendation_score if offer else None,
        },
        "audit_log": [
            {
                "id": item.id,
                "stage_key": item.stage_key,
                "event_type": item.event_type,
                "actor_type": item.actor_type,
                "actor_email": item.actor_email,
                "summary": item.summary,
                "detail": parse_json(item.detail_json, {}),
                "created_at": dt_iso(item.created_at),
            }
            for item in audit_log
        ],
        "offer_workflow": _serialize_offer(offer),
        "application_documents": application_documents,
        "verification_case": {
            "id": verification_case.id,
            "status": verification_case.status,
            "review_summary": verification_case.review_summary,
            "document_items": verification_documents,
        } if verification_case else None,
    }


def _serialize_offer(offer: OfferWorkflow | None) -> dict[str, Any] | None:
    if not offer:
        return None
    return {
        "id": offer.id,
        "application_id": offer.application_id,
        "token": offer.token,
        "status": offer.status,
        "joining_date": offer.joining_date,
        "joining_date_history": parse_json(offer.joining_date_history_json, []),
        "onboarding_instructions": offer.onboarding_instructions,
        "work_mode": offer.work_mode,
        "employment_type": offer.employment_type,
        "reporting_manager": offer.reporting_manager,
        "reporting_team": offer.reporting_team,
        "compensation_text": offer.compensation_text,
        "offered_compensation": offer.offered_compensation,
        "contract_duration_or_notes": offer.contract_duration_or_notes,
        "designation": offer.designation,
        "department": offer.department,
        "company_details": offer.company_details,
        "work_location": offer.work_location,
        "hr_contact_details": offer.hr_contact_details,
        "terms_and_conditions": offer.terms_and_conditions,
        "offer_valid_until": offer.offer_valid_until,
        "candidate_portal_expires_at": dt_iso(offer.candidate_portal_expires_at),
        "bgv_initiated_at": dt_iso(offer.bgv_initiated_at),
        "bgv_started_by": offer.bgv_started_by,
        "offer_generated_at": dt_iso(offer.offer_generated_at),
        "unsigned_pdf_path": offer.unsigned_pdf_path,
        "signed_pdf_path": offer.signed_pdf_path,
        "offer_sent_at": dt_iso(offer.offer_sent_at),
        "offer_email_to": offer.offer_email_to,
        "offer_link_opened_at": dt_iso(offer.offer_link_opened_at),
        "candidate_response": offer.candidate_response,
        "candidate_response_at": dt_iso(offer.candidate_response_at),
        "candidate_remarks": offer.candidate_remarks,
        "signature_image_path": offer.signature_image_path,
        "signature_type": offer.signature_type,
        "candidate_ip": offer.candidate_ip,
        "candidate_user_agent": offer.candidate_user_agent,
        "hr_final_approval_status": offer.hr_final_approval_status,
        "hr_final_approval_at": dt_iso(offer.hr_final_approval_at),
        "hr_final_approver": offer.hr_final_approver,
        "hr_final_approval_reason": offer.hr_final_approval_reason,
        "final_outcome": offer.final_outcome,
        "final_outcome_summary": offer.final_outcome_summary,
        "final_recommendation_score": offer.final_recommendation_score,
        "onboarding_status": offer.onboarding_status,
        "onboarding_notes": offer.onboarding_notes,
        "onboarding_started_at": dt_iso(offer.onboarding_started_at),
        "onboarding_completed_at": dt_iso(offer.onboarding_completed_at),
        "created_at": dt_iso(offer.created_at),
        "updated_at": dt_iso(offer.updated_at),
    }


def offer_storage_root() -> str:
    return os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "uploads", "offers")
