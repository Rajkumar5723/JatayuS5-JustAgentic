"""
core/mcq_evidence_tracker.py
=============================
Tracks question-level evidence and malpractice incidents.
"""
import logging
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.models import (
    MCQQuestionAnswer,
    MalpracticeIncident,
    IncidentEvidence,
    EvidenceFile
)
from core.evidence_storage import EvidenceStorageService

logger = logging.getLogger(__name__)


class MCQEvidenceTracker:
    """Tracks question-level evidence and malpractice incidents."""

    def __init__(self, db_session: Session, evidence_storage: EvidenceStorageService):
        self.db = db_session
        self.evidence_storage = evidence_storage

    def record_question_answer(
        self,
        session_token: str,
        question_id: int,
        selected_answer: str,
        is_correct: bool,
        time_spent_seconds: int
    ) -> None:
        """Record MCQ question answer with timing."""
        try:
            answer = MCQQuestionAnswer(
                session_token=session_token,
                question_id=question_id,
                selected_answer=selected_answer,
                is_correct=is_correct,
                time_spent_seconds=time_spent_seconds,
                answered_at=datetime.now(timezone.utc)
            )
            self.db.add(answer)
            self.db.commit()
            logger.info(f"Recorded answer for question {question_id} in session {session_token}")
        except Exception as e:
            logger.error(f"Failed to record question answer: {e}")
            self.db.rollback()

    async def record_malpractice_incident(
        self,
        session_token: str,
        question_id: Optional[int],
        incident_type: str,
        severity: str,
        confidence_score: float,
        agent_name: str,
        reason_text: str,
        evidence_files: List[dict]  # [{type, data, mime_type}, ...]
    ) -> Optional[int]:
        """
        Record malpractice incident with evidence.
        Returns incident ID on success, None on failure.
        """
        try:
            # Create incident
            incident = MalpracticeIncident(
                session_token=session_token,
                question_id=question_id,
                incident_type=incident_type,
                severity=severity,
                confidence_score=confidence_score,
                agent_name=agent_name,
                reason_text=reason_text,
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(incident)
            self.db.flush()  # Get incident ID

            # Upload evidence files and link to incident
            evidence_file_ids = []
            for idx, evidence in enumerate(evidence_files):
                s3_key = await self.evidence_storage.upload_evidence(
                    session_token=session_token,
                    evidence_type=evidence['type'],
                    file_data=evidence['data'],
                    mime_type=evidence['mime_type'],
                    metadata={'incident_id': incident.id, 'agent_name': agent_name}
                )

                if s3_key:
                    # Get evidence file ID from database
                    evidence_file = self.db.query(EvidenceFile).filter(
                        EvidenceFile.s3_key == s3_key
                    ).first()

                    if evidence_file:
                        evidence_file_ids.append((evidence_file.id, idx))

            # Link evidence to incident
            if evidence_file_ids:
                self.link_evidence_to_incident(incident.id, evidence_file_ids)

            self.db.commit()
            logger.info(f"Recorded malpractice incident {incident.id} with {len(evidence_file_ids)} evidence files")
            return incident.id

        except Exception as e:
            logger.error(f"Failed to record malpractice incident: {e}")
            self.db.rollback()
            return None

    def link_evidence_to_incident(
        self,
        incident_id: int,
        evidence_file_ids: List[tuple]  # [(file_id, sequence_order), ...]
    ) -> None:
        """Link multiple evidence files to an incident with ordering."""
        try:
            for file_id, sequence_order in evidence_file_ids:
                link = IncidentEvidence(
                    incident_id=incident_id,
                    evidence_file_id=file_id,
                    sequence_order=sequence_order
                )
                self.db.add(link)
            self.db.commit()
            logger.info(f"Linked {len(evidence_file_ids)} evidence files to incident {incident_id}")
        except Exception as e:
            logger.error(f"Failed to link evidence to incident: {e}")
            self.db.rollback()

    def get_question_evidence(
        self,
        session_token: str,
        question_id: int
    ) -> List[dict]:
        """Retrieve all evidence for a specific question."""
        try:
            # Get all incidents for this question
            incidents = self.db.query(MalpracticeIncident).filter(
                MalpracticeIncident.session_token == session_token,
                MalpracticeIncident.question_id == question_id
            ).all()

            result = []
            for incident in incidents:
                # Get evidence files for this incident
                evidence_links = self.db.query(IncidentEvidence).filter(
                    IncidentEvidence.incident_id == incident.id
                ).order_by(IncidentEvidence.sequence_order).all()

                evidence_files = []
                for link in evidence_links:
                    evidence_file = self.db.query(EvidenceFile).filter(
                        EvidenceFile.id == link.evidence_file_id
                    ).first()

                    if evidence_file:
                        # Generate presigned URL
                        presigned_url = self.evidence_storage.generate_presigned_url(evidence_file.s3_key)
                        evidence_files.append({
                            'id': evidence_file.id,
                            'type': evidence_file.evidence_type,
                            's3_key': evidence_file.s3_key,
                            'presigned_url': presigned_url,
                            'mime_type': evidence_file.mime_type,
                            'file_size_bytes': evidence_file.file_size_bytes,
                            'created_at': evidence_file.created_at.isoformat()
                        })

                result.append({
                    'incident_id': incident.id,
                    'incident_type': incident.incident_type,
                    'severity': incident.severity,
                    'confidence_score': incident.confidence_score,
                    'agent_name': incident.agent_name,
                    'reason_text': incident.reason_text,
                    'created_at': incident.created_at.isoformat(),
                    'evidence_files': evidence_files
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get question evidence: {e}")
            return []

    def get_session_incidents(self, session_token: str) -> List[dict]:
        """Get all incidents for a session with evidence."""
        try:
            incidents = self.db.query(MalpracticeIncident).filter(
                MalpracticeIncident.session_token == session_token
            ).order_by(MalpracticeIncident.created_at).all()

            result = []
            for incident in incidents:
                evidence_links = self.db.query(IncidentEvidence).filter(
                    IncidentEvidence.incident_id == incident.id
                ).order_by(IncidentEvidence.sequence_order).all()

                evidence_files = []
                for link in evidence_links:
                    evidence_file = self.db.query(EvidenceFile).filter(
                        EvidenceFile.id == link.evidence_file_id
                    ).first()

                    if evidence_file:
                        presigned_url = self.evidence_storage.generate_presigned_url(evidence_file.s3_key)
                        evidence_files.append({
                            'id': evidence_file.id,
                            'type': evidence_file.evidence_type,
                            's3_key': evidence_file.s3_key,
                            'presigned_url': presigned_url,
                            'mime_type': evidence_file.mime_type
                        })

                result.append({
                    'incident_id': incident.id,
                    'question_id': incident.question_id,
                    'incident_type': incident.incident_type,
                    'severity': incident.severity,
                    'confidence_score': incident.confidence_score,
                    'agent_name': incident.agent_name,
                    'reason_text': incident.reason_text,
                    'created_at': incident.created_at.isoformat(),
                    'evidence_files': evidence_files
                })

            return result

        except Exception as e:
            logger.error(f"Failed to get session incidents: {e}")
            return []
