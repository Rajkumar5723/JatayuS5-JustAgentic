from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
from collections import Counter
from typing import Any

from core.models import ProctoringEvidence
from core.evidence_storage import EvidenceStorageService
from core.s3_manager import get_s3_manager

try:
    from PIL import Image  # type: ignore
except Exception:  # pragma: no cover - optional dependency
    Image = None


RISK_WEIGHTS: dict[str, float] = {
    "tab_hidden": 2,
    "window_blur": 2,
    "fullscreen_exit": 4,
    "copy": 2,
    "paste": 3,
    "devtools_suspected": 5,
    "camera_error": 6,
    "permissions_denied": 7,
    "screen_capture_unavailable": 7,
    "screen_share_stopped": 6,
    "face_mismatch": 5,
    "manual_flag": 6,
}

RISK_CAPS: dict[str, int] = {
    "tab_hidden": 3,
    "window_blur": 3,
    "fullscreen_exit": 2,
    "copy": 2,
    "paste": 2,
    "devtools_suspected": 2,
    "camera_error": 2,
    "permissions_denied": 1,
    "screen_capture_unavailable": 1,
    "screen_share_stopped": 2,
    "face_mismatch": 3,
    "manual_flag": 2,
}

LOW_FACE_SIMILARITY = 0.55
HARD_BLOCK_EVENTS = {
    "permissions_denied": "camera_or_permission_denied",
    "screen_capture_unavailable": "screen_capture_required",
    "screen_share_stopped": "screen_share_stopped",
}
PAYLOAD_MEDIA_FIELDS = (
    ("face_b64", "face_storage_key", "face_capture"),
    ("screen_b64", "screen_storage_key", "screen_capture"),
    ("snapshot_b64", "snapshot_storage_key", "interview_snapshot"),
)


def _from_data_url(value: str | None) -> bytes:
    if not value:
        return b""
    data = value.split(",", 1)[1] if value.startswith("data:") and "," in value else value
    try:
        return base64.b64decode(data)
    except Exception:
        return b""


def _average_hash(raw: bytes) -> str | None:
    if not raw:
        return None
    if Image is None:
        return hashlib.sha256(raw).hexdigest()

    try:
        with Image.open(io.BytesIO(raw)) as img:
            pixels = list(img.convert("L").resize((8, 8)).getdata())
    except Exception:
        return hashlib.sha256(raw).hexdigest()

    avg = sum(pixels) / len(pixels)
    bits = "".join("1" if px >= avg else "0" for px in pixels)
    return bits


def image_similarity(reference_b64: str | None, candidate_b64: str | None) -> float | None:
    ref_hash = _average_hash(_from_data_url(reference_b64))
    cand_hash = _average_hash(_from_data_url(candidate_b64))
    if not ref_hash or not cand_hash:
        return None
    if len(ref_hash) != len(cand_hash):
        return 1.0 if ref_hash == cand_hash else 0.0
    distance = sum(1 for a, b in zip(ref_hash, cand_hash) if a != b)
    return round(max(0.0, 1 - (distance / len(ref_hash))), 3)


def _persist_payload_media(db, session_token: str, payload: dict[str, Any]) -> dict[str, Any]:
    if not any(payload.get(source_key) for source_key, _, _ in PAYLOAD_MEDIA_FIELDS):
        return payload

    try:
        storage = EvidenceStorageService(get_s3_manager(), db)
    except Exception:
        return payload

    next_payload = dict(payload)
    for source_key, storage_key_name, capture_type in PAYLOAD_MEDIA_FIELDS:
        inline_value = next_payload.get(source_key)
        if not inline_value:
            continue

        file_data = _from_data_url(str(inline_value))
        if not file_data:
            continue

        try:
            storage_key = asyncio.run(
                storage.upload_evidence(
                    session_token=session_token,
                    evidence_type="photo",
                    file_data=file_data,
                    mime_type="image/jpeg",
                    metadata={"capture_type": capture_type, "source_key": source_key},
                )
            )
        except Exception:
            storage_key = None

        if storage_key:
            next_payload[storage_key_name] = storage_key
            next_payload.pop(source_key, None)

    return next_payload


def _risk_level(score: float) -> str:
    if score >= 12:
        return "severe"
    if score >= 9:
        return "critical"
    if score >= 6:
        return "high"
    if score >= 3:
        return "medium"
    return "low"


def _block_reason(counts: Counter[str], score: float) -> str:
    if counts.get("permissions_denied"):
        return "camera_or_permission_denied"
    if counts.get("screen_capture_unavailable"):
        return "screen_capture_required"
    if counts.get("screen_share_stopped"):
        return "screen_share_stopped"
    if counts.get("camera_error", 0) >= 2:
        return "camera_unavailable"
    if counts.get("devtools_suspected"):
        return "developer_tools_detected"
    if counts.get("fullscreen_exit", 0) >= 2:
        return "fullscreen_broken_repeatedly"
    if counts.get("face_mismatch"):
        return "face_continuity_low"
    if score >= 12:
        return "risk_threshold_reached"
    return ""


def summarize_proctoring(rows: list[ProctoringEvidence]) -> dict[str, Any]:
    counts: Counter[str] = Counter()
    score = 0.0
    face_scores: list[float] = []

    for row in rows:
        counts[row.event_type] += 1
        capped_count = min(counts[row.event_type], RISK_CAPS.get(row.event_type, counts[row.event_type]))
        if capped_count == counts[row.event_type]:
            score += row.risk_delta or 0

        try:
            payload = json.loads(row.evidence_json or "{}")
        except Exception:
            payload = {}
        sim = payload.get("face_similarity")
        if isinstance(sim, (int, float)):
            face_scores.append(float(sim))

    level = _risk_level(score)
    hard_block_reason = next(
        (reason for event_type, reason in HARD_BLOCK_EVENTS.items() if counts.get(event_type)),
        "",
    )
    blocked = bool(hard_block_reason) or level == "severe"
    if blocked and level != "severe":
        level = "severe"
    return {
        "risk_score": round(score, 2),
        "risk_level": level,
        "blocked": blocked,
        "block_reason": hard_block_reason or _block_reason(counts, score),
        "event_counts": dict(counts),
        "face_continuity_score": round(sum(face_scores) / len(face_scores), 3) if face_scores else None,
    }


def record_event(
    db,
    *,
    session,
    event_type: str,
    payload: dict[str, Any] | None = None,
    round_name: str,
    application_id: int | None = None,
    test_session_id: int | None = None,
    coding_session_id: int | None = None,
    live_session_id: int | None = None,
) -> dict[str, Any]:
    payload = dict(payload or {})
    face_b64 = payload.get("face_b64")
    if face_b64 and not getattr(session, "verification_face_b64", None):
        session.verification_face_b64 = face_b64

    derived_event_type = event_type
    risk_delta = RISK_WEIGHTS.get(event_type, 0)
    face_similarity = None

    if face_b64 and getattr(session, "verification_face_b64", None):
        face_similarity = image_similarity(session.verification_face_b64, face_b64)
        if face_similarity is not None:
            payload["face_similarity"] = face_similarity
            existing_score = getattr(session, "face_continuity_score", None) or 0
            session.face_continuity_score = max(existing_score, face_similarity)
            if event_type == "snapshot_captured" and face_similarity < LOW_FACE_SIMILARITY:
                derived_event_type = "face_mismatch"
                risk_delta = RISK_WEIGHTS["face_mismatch"]
                payload["derived_from_snapshot"] = True

    payload = _persist_payload_media(db, session.token, payload)

    evidence = ProctoringEvidence(
        application_id=application_id,
        test_session_id=test_session_id,
        coding_session_id=coding_session_id,
        live_session_id=live_session_id,
        session_token=session.token,
        round_name=round_name,
        event_type=derived_event_type,
        severity=_risk_level(risk_delta),
        risk_delta=risk_delta,
        evidence_json=json.dumps(payload),
    )
    db.add(evidence)
    db.flush()

    rows = (
        db.query(ProctoringEvidence)
        .filter(ProctoringEvidence.session_token == session.token)
        .order_by(ProctoringEvidence.created_at.asc(), ProctoringEvidence.id.asc())
        .all()
    )
    summary = summarize_proctoring(rows)
    session.proctoring_risk = summary["risk_level"]
    if hasattr(session, "risk_score"):
        session.risk_score = summary["risk_score"]
    if hasattr(session, "block_reason"):
        session.block_reason = summary["block_reason"]
    if hasattr(session, "proctoring_json"):
        session.proctoring_json = json.dumps(summary)
    if summary["face_continuity_score"] is not None and hasattr(session, "face_continuity_score"):
        session.face_continuity_score = summary["face_continuity_score"]

    db.commit()
    return summary
