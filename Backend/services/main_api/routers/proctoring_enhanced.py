"""
services/main_api/routers/proctoring_enhanced.py
=================================================
Enhanced proctoring endpoints for QR verification, room scanning, and reconnection.
"""
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

from core.config import settings
from core.database import get_db
from core.models import User, RoomScan, ReconnectLog, OfflineRecording
from core.qr_verification import QRVerificationService
from core.room_scan_gate import get_latest_room_scan
from core.room_scan_analyzer import RoomScanAnalyzer
from core.reconnect_service import ReconnectService
from core.s3_manager import get_s3_manager
from core.evidence_storage import EvidenceStorageService
from core.agents import DeviceFingerprintAgent, DisconnectPatternAgent
from groq import Groq

router = APIRouter(prefix="/proctoring", tags=["proctoring"])


def build_groq_client() -> Groq:
    if not settings.GROQ_API_KEY:
        raise RuntimeError("GROQ_API_KEY is not configured")
    return Groq(api_key=settings.GROQ_API_KEY)


# Pydantic models
class QRGenerateRequest(BaseModel):
    session_token: str
    verification_type: str = "initial"  # initial or re-verification


class QRValidateRequest(BaseModel):
    token: str


class RoomScanUploadRequest(BaseModel):
    session_token: str
    scan_type: str
    frame_count: int


class ReconnectRequest(BaseModel):
    session_token: str
    disconnect_timestamp: str
    reconnect_timestamp: str
    device_fingerprint_before: str
    device_fingerprint_after: str
    risk_score_before: float


# QR Verification Endpoints
@router.post("/qr/generate")
async def generate_qr_code(
    request: QRGenerateRequest,
    db: Session = Depends(get_db)
):
    """Generate QR code for 360-degree room verification."""
    try:
        qr_service = QRVerificationService()
        qr_token = qr_service.create_jwt_token(
            request.session_token,
            request.verification_type
        )
        qr_code_base64 = qr_service.generate_qr_code(
            request.session_token,
            request.verification_type,
            token=qr_token,
        )

        return {
            "qr_code": qr_code_base64,
            "qr_token": qr_token,
            "verification_url": qr_service.build_verification_url(qr_token),
            "session_token": request.session_token,
            "verification_type": request.verification_type,
            "expires_in_minutes": qr_service.jwt_expiration_minutes
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to generate QR code: {str(e)}")


@router.post("/qr/validate")
async def validate_qr_token(
    request: QRValidateRequest,
    db: Session = Depends(get_db)
):
    """Validate JWT token from scanned QR code."""
    try:
        qr_service = QRVerificationService()
        payload = qr_service.validate_jwt_token(request.token)

        # Create mobile camera session
        mobile_session_id = qr_service.create_mobile_camera_session(
            payload["session_token"],
            payload["verification_type"]
        )

        return {
            "valid": True,
            "session_token": payload["session_token"],
            "verification_type": payload["verification_type"],
            "mobile_session_id": mobile_session_id,
            "timestamp": payload["timestamp"]
        }

    except ValueError as e:
        error_code = str(e)
        return {
            "valid": False,
            "error": error_code,
            "message": {
                "JWT_EXPIRED": "QR code has expired. Please generate a new one.",
                "JWT_INVALID_SIGNATURE": "Invalid QR code signature.",
                "JWT_MALFORMED": "QR code is malformed.",
            }.get(error_code, "QR code validation failed.")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to validate QR token: {str(e)}")


# Room Scan Endpoints
@router.post("/360/upload")
async def upload_room_scan_frames(
    session_token: str,
    scan_type: str,
    qr_token: str,
    files: List[UploadFile] = File(...),
    db: Session = Depends(get_db)
):
    """Upload 360-degree room scan frames for analysis."""
    try:
        qr_service = QRVerificationService()
        payload = qr_service.validate_jwt_token(qr_token)
        if payload.get("session_token") != session_token:
            raise HTTPException(status_code=400, detail="QR token does not match this test session.")
        if (payload.get("verification_type") or "initial") != scan_type:
            raise HTTPException(status_code=400, detail="QR token does not match this verification type.")

        # Read frame data
        frames = []
        for file in files:
            frame_data = await file.read()
            frames.append(frame_data)

        # Initialize analyzer
        groq_client = build_groq_client()
        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)
        analyzer = RoomScanAnalyzer(groq_client, storage, db)

        # Analyze scan
        report = await analyzer.analyze_scan(session_token, frames, scan_type)

        return {
            "session_token": session_token,
            "scan_type": scan_type,
            "frames_uploaded": len(frames),
            "analysis_complete": True,
            "report": report
        }
    except HTTPException:
        raise
    except ValueError as exc:
        error_code = str(exc)
        raise HTTPException(
            status_code=400,
            detail={
                "JWT_EXPIRED": "QR code has expired. Please generate a new one.",
                "JWT_INVALID_SIGNATURE": "QR code signature is invalid.",
                "JWT_MALFORMED": "QR code is malformed.",
            }.get(error_code, "QR validation failed."),
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload room scan: {str(e)}")


@router.get("/360/status/{session_token}")
async def get_room_scan_status(
    session_token: str,
    scan_type: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Get status of room scan analysis."""
    try:
        room_scan = get_latest_room_scan(db, session_token, scan_type or "")

        if not room_scan:
            return {
                "session_token": session_token,
                "scan_exists": False,
                "scan_type": scan_type,
            }

        return {
            "session_token": session_token,
            "scan_exists": True,
            "scan_id": room_scan.id,
            "scan_type": room_scan.scan_type,
            "scan_status": room_scan.scan_status,
            "verdict": room_scan.verdict,
            "created_at": room_scan.created_at.isoformat(),
            "completed_at": room_scan.completed_at.isoformat() if room_scan.completed_at else None
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get room scan status: {str(e)}")


# Reconnection Endpoints
@router.post("/reconnect")
async def handle_reconnection(
    request: ReconnectRequest,
    db: Session = Depends(get_db)
):
    """Handle reconnection after network gap."""
    try:
        # Initialize agents
        groq_client = build_groq_client()
        device_agent = DeviceFingerprintAgent(groq_client)
        disconnect_agent = DisconnectPatternAgent(groq_client)

        # Initialize reconnect service
        reconnect_service = ReconnectService(db, device_agent, disconnect_agent)

        # Parse timestamps
        disconnect_ts = datetime.fromisoformat(request.disconnect_timestamp)
        reconnect_ts = datetime.fromisoformat(request.reconnect_timestamp)

        # Handle reconnect
        result = await reconnect_service.handle_reconnect(
            request.session_token,
            disconnect_ts,
            reconnect_ts,
            request.device_fingerprint_before,
            request.device_fingerprint_after,
            request.risk_score_before
        )

        return result

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to handle reconnection: {str(e)}")


@router.post("/gap-video/upload")
async def upload_gap_video(
    session_token: str,
    camera_gap_id: int,
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """Upload offline gap recording for forensic analysis."""
    try:
        # Read video data
        video_data = await file.read()

        # Upload to S3
        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)

        s3_key = await storage.upload_evidence(
            session_token=session_token,
            evidence_type="video",
            file_data=video_data,
            mime_type="video/webm",
            metadata={"camera_gap_id": camera_gap_id, "type": "offline_recording"}
        )

        if not s3_key:
            raise HTTPException(status_code=500, detail="Failed to upload video to S3")

        # Create offline recording record
        offline_recording = OfflineRecording(
            session_token=session_token,
            camera_gap_id=camera_gap_id,
            s3_key=s3_key,
            file_size_bytes=len(video_data),
            analysis_status="pending"
        )
        db.add(offline_recording)
        db.commit()

        # Queue for analysis
        groq_client = build_groq_client()
        device_agent = DeviceFingerprintAgent(groq_client)
        disconnect_agent = DisconnectPatternAgent(groq_client)
        reconnect_service = ReconnectService(db, device_agent, disconnect_agent)

        await reconnect_service.queue_gap_analysis(camera_gap_id, s3_key)

        return {
            "session_token": session_token,
            "camera_gap_id": camera_gap_id,
            "s3_key": s3_key,
            "file_size_bytes": len(video_data),
            "analysis_status": "queued",
            "offline_recording_id": offline_recording.id
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to upload gap video: {str(e)}")


@router.get("/gap-analysis/{gap_id}")
async def get_gap_analysis(
    gap_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve gap analysis results."""
    try:
        # Get reconnect log
        reconnect_log = db.query(ReconnectLog).filter(
            ReconnectLog.id == gap_id
        ).first()

        if not reconnect_log:
            raise HTTPException(status_code=404, detail="Gap analysis not found")

        # Get offline recording if exists
        offline_recording = db.query(OfflineRecording).filter(
            OfflineRecording.camera_gap_id == gap_id
        ).first()

        return {
            "gap_id": gap_id,
            "session_token": reconnect_log.session_token,
            "disconnect_timestamp": reconnect_log.disconnect_timestamp.isoformat(),
            "reconnect_timestamp": reconnect_log.reconnect_timestamp.isoformat(),
            "gap_duration_seconds": reconnect_log.gap_duration_seconds,
            "fingerprint_match": reconnect_log.fingerprint_match,
            "disconnect_verdict": reconnect_log.disconnect_verdict,
            "gap_video_verdict": reconnect_log.gap_video_verdict,
            "combined_verdict": reconnect_log.combined_verdict,
            "risk_penalty": reconnect_log.risk_penalty,
            "analysis_completed": reconnect_log.analysis_completed,
            "offline_recording": {
                "exists": offline_recording is not None,
                "analysis_status": offline_recording.analysis_status if offline_recording else None,
                "s3_key": offline_recording.s3_key if offline_recording else None
            } if offline_recording else None
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve gap analysis: {str(e)}")
