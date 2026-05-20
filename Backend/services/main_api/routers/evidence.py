"""
services/main_api/routers/evidence.py
======================================
Evidence retrieval API endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from typing import List

from core.database import get_db
from core.models import (
    MalpracticeIncident,
    IncidentEvidence,
    EvidenceFile,
    AgentDecisionLog
)
from core.s3_manager import get_s3_manager
from core.evidence_storage import EvidenceStorageService, resolve_local_evidence_path

router = APIRouter(prefix="/evidence", tags=["evidence"])


@router.get("/files")
async def get_local_evidence_file(key: str):
    path = resolve_local_evidence_path(key)
    if not path or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="Evidence file not found")
    return FileResponse(path)


@router.get("/incident/{incident_id}")
async def get_incident_evidence(
    incident_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve evidence for a specific incident with presigned URLs."""
    try:
        # Get incident
        incident = db.query(MalpracticeIncident).filter(
            MalpracticeIncident.id == incident_id
        ).first()

        if not incident:
            raise HTTPException(status_code=404, detail="Incident not found")

        # Get evidence files
        evidence_links = db.query(IncidentEvidence).filter(
            IncidentEvidence.incident_id == incident_id
        ).order_by(IncidentEvidence.sequence_order).all()

        evidence_files = []
        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)

        for link in evidence_links:
            evidence_file = db.query(EvidenceFile).filter(
                EvidenceFile.id == link.evidence_file_id
            ).first()

            if evidence_file:
                presigned_url = storage.generate_presigned_url(evidence_file.s3_key)
                evidence_files.append({
                    "id": evidence_file.id,
                    "type": evidence_file.evidence_type,
                    "s3_key": evidence_file.s3_key,
                    "presigned_url": presigned_url,
                    "mime_type": evidence_file.mime_type,
                    "file_size_bytes": evidence_file.file_size_bytes,
                    "created_at": evidence_file.created_at.isoformat()
                })

        return {
            "incident_id": incident.id,
            "session_token": incident.session_token,
            "question_id": incident.question_id,
            "incident_type": incident.incident_type,
            "severity": incident.severity,
            "confidence_score": incident.confidence_score,
            "agent_name": incident.agent_name,
            "reason_text": incident.reason_text,
            "created_at": incident.created_at.isoformat(),
            "evidence_files": evidence_files
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve evidence: {str(e)}")


@router.get("/question/{session_token}/{question_id}")
async def get_question_evidence(
    session_token: str,
    question_id: int,
    db: Session = Depends(get_db)
):
    """Retrieve all evidence for a specific question."""
    try:
        # Get all incidents for this question
        incidents = db.query(MalpracticeIncident).filter(
            MalpracticeIncident.session_token == session_token,
            MalpracticeIncident.question_id == question_id
        ).all()

        result = []
        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)

        for incident in incidents:
            # Get evidence files
            evidence_links = db.query(IncidentEvidence).filter(
                IncidentEvidence.incident_id == incident.id
            ).order_by(IncidentEvidence.sequence_order).all()

            evidence_files = []
            for link in evidence_links:
                evidence_file = db.query(EvidenceFile).filter(
                    EvidenceFile.id == link.evidence_file_id
                ).first()

                if evidence_file:
                    presigned_url = storage.generate_presigned_url(evidence_file.s3_key)
                    evidence_files.append({
                        "id": evidence_file.id,
                        "type": evidence_file.evidence_type,
                        "presigned_url": presigned_url,
                        "mime_type": evidence_file.mime_type
                    })

            result.append({
                "incident_id": incident.id,
                "incident_type": incident.incident_type,
                "severity": incident.severity,
                "confidence_score": incident.confidence_score,
                "agent_name": incident.agent_name,
                "reason_text": incident.reason_text,
                "created_at": incident.created_at.isoformat(),
                "evidence_files": evidence_files
            })

        return {
            "session_token": session_token,
            "question_id": question_id,
            "total_incidents": len(result),
            "incidents": result
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve question evidence: {str(e)}")


@router.get("/session/{session_token}")
async def get_session_evidence(
    session_token: str,
    db: Session = Depends(get_db)
):
    """Retrieve chronological timeline of all evidence for a session."""
    try:
        # Get all incidents
        incidents = db.query(MalpracticeIncident).filter(
            MalpracticeIncident.session_token == session_token
        ).order_by(MalpracticeIncident.created_at).all()

        # Get all agent decisions
        agent_decisions = db.query(AgentDecisionLog).filter(
            AgentDecisionLog.session_token == session_token
        ).order_by(AgentDecisionLog.created_at).all()

        manager = get_s3_manager()
        storage = EvidenceStorageService(manager, db)

        # Build timeline
        timeline = []

        for incident in incidents:
            evidence_links = db.query(IncidentEvidence).filter(
                IncidentEvidence.incident_id == incident.id
            ).order_by(IncidentEvidence.sequence_order).all()

            evidence_files = []
            for link in evidence_links:
                evidence_file = db.query(EvidenceFile).filter(
                    EvidenceFile.id == link.evidence_file_id
                ).first()

                if evidence_file:
                    presigned_url = storage.generate_presigned_url(evidence_file.s3_key)
                    evidence_files.append({
                        "type": evidence_file.evidence_type,
                        "presigned_url": presigned_url,
                        "mime_type": evidence_file.mime_type
                    })

            timeline.append({
                "timestamp": incident.created_at.isoformat(),
                "type": "incident",
                "incident_id": incident.id,
                "question_id": incident.question_id,
                "incident_type": incident.incident_type,
                "severity": incident.severity,
                "confidence_score": incident.confidence_score,
                "agent_name": incident.agent_name,
                "reason_text": incident.reason_text,
                "evidence_files": evidence_files
            })

        # Add agent decisions to timeline
        for decision in agent_decisions:
            timeline.append({
                "timestamp": decision.created_at.isoformat(),
                "type": "agent_decision",
                "agent_name": decision.agent_name,
                "detection_type": decision.detection_type,
                "confidence_score": decision.confidence_score,
                "reasoning_text": decision.reasoning_text,
                "processing_time_ms": decision.processing_time_ms
            })

        # Sort timeline by timestamp
        timeline.sort(key=lambda x: x["timestamp"])

        return {
            "session_token": session_token,
            "total_incidents": len(incidents),
            "total_agent_decisions": len(agent_decisions),
            "timeline": timeline
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve session evidence: {str(e)}")


@router.get("/agent-health")
async def get_agent_health(
    db: Session = Depends(get_db)
):
    """Get agent health metrics and statistics."""
    try:
        # Get agent statistics
        from sqlalchemy import func

        agent_stats = db.query(
            AgentDecisionLog.agent_name,
            func.count(AgentDecisionLog.id).label("total_decisions"),
            func.avg(AgentDecisionLog.confidence_score).label("avg_confidence"),
            func.avg(AgentDecisionLog.processing_time_ms).label("avg_processing_time")
        ).group_by(AgentDecisionLog.agent_name).all()

        stats = []
        for stat in agent_stats:
            stats.append({
                "agent_name": stat.agent_name,
                "total_decisions": stat.total_decisions,
                "avg_confidence": round(stat.avg_confidence, 3) if stat.avg_confidence else 0,
                "avg_processing_time_ms": round(stat.avg_processing_time, 2) if stat.avg_processing_time else 0
            })

        return {
            "agent_statistics": stats,
            "total_agents": len(stats)
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve agent health: {str(e)}")
