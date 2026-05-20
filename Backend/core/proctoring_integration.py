"""
core/proctoring_integration.py
===============================
Integration layer for enhanced proctoring with all test types.
Provides unified interface for MCQ, Coding, and Live HR tests.
"""
import logging
import asyncio
from typing import Optional, List
from datetime import datetime, timezone

from sqlalchemy.orm import Session
from groq import Groq
import os

from core.models import TestSession, CodingSession, LiveSession
from core.s3_manager import get_s3_manager
from core.evidence_storage import EvidenceStorageService
from core.mcq_evidence_tracker import MCQEvidenceTracker
from core.real_time_monitor import RealTimeMonitor
from core.agents import (
    FaceTrackingAgent,
    ObjectDetectionAgent,
    AudioAnalysisAgent,
    BehaviorAnomalyAgent
)

logger = logging.getLogger(__name__)


class EnhancedProctoringSession:
    """
    Unified proctoring session for all test types.
    Handles real-time monitoring, evidence collection, and incident tracking.
    """

    def __init__(
        self,
        session_token: str,
        session_type: str,  # "mcq", "coding", "live_hr"
        db_session: Session
    ):
        self.session_token = session_token
        self.session_type = session_type
        self.db = db_session
        self.current_question_id: Optional[int] = None

        # Initialize components
        self._initialize_components()

    def _initialize_components(self):
        """Initialize all proctoring components."""
        try:
            # Initialize S3 and evidence storage
            self.s3_manager = get_s3_manager()
            self.evidence_storage = EvidenceStorageService(self.s3_manager, self.db)

            # Initialize evidence tracker
            self.evidence_tracker = MCQEvidenceTracker(self.db, self.evidence_storage)

            # Initialize Groq client
            groq_api_key = os.getenv("GROQ_API_KEY")
            self.groq_client = Groq(api_key=groq_api_key) if groq_api_key else None

            # Initialize AI agents
            self.agents = [
                FaceTrackingAgent(self.groq_client),
                ObjectDetectionAgent(self.groq_client),
                AudioAnalysisAgent(self.groq_client),
                BehaviorAnomalyAgent(self.groq_client)
            ]

            # Initialize real-time monitor
            self.monitor = RealTimeMonitor(self.agents, self.evidence_tracker)

            # Start evidence upload queue processor
            self.evidence_storage.start_queue_processor()

            logger.info(f"Enhanced proctoring initialized for {self.session_token} ({self.session_type})")

        except Exception as e:
            logger.error(f"Failed to initialize proctoring components: {e}")
            raise

    async def process_frame(
        self,
        frame_data: bytes,
        question_id: Optional[int] = None
    ) -> dict:
        """
        Process a video frame through all AI agents.
        Returns detection results and updates risk score.
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()

            # Use current question ID if not provided
            if question_id is None:
                question_id = self.current_question_id

            # Process frame through monitor
            results = await self.monitor.process_frame(
                session_token=self.session_token,
                question_id=question_id,
                frame_data=frame_data,
                timestamp=timestamp
            )

            # Update session risk score
            self._update_session_risk()

            return {
                "processed": True,
                "detections": len(results),
                "results": results,
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"Frame processing failed: {e}")
            return {
                "processed": False,
                "error": str(e)
            }

    async def process_audio(
        self,
        audio_data: bytes,
        question_id: Optional[int] = None
    ) -> dict:
        """
        Process an audio chunk through audio analysis agents.
        Returns detection results.
        """
        try:
            timestamp = datetime.now(timezone.utc).timestamp()

            if question_id is None:
                question_id = self.current_question_id

            # Process audio through monitor
            results = await self.monitor.process_audio_chunk(
                session_token=self.session_token,
                question_id=question_id,
                audio_data=audio_data,
                timestamp=timestamp
            )

            # Update session risk score
            self._update_session_risk()

            return {
                "processed": True,
                "detections": len(results),
                "results": results,
                "timestamp": timestamp
            }

        except Exception as e:
            logger.error(f"Audio processing failed: {e}")
            return {
                "processed": False,
                "error": str(e)
            }

    def record_question_answer(
        self,
        question_id: int,
        selected_answer: str,
        is_correct: bool,
        time_spent_seconds: int
    ) -> None:
        """Record MCQ question answer (for MCQ and Coding tests)."""
        try:
            self.current_question_id = question_id
            self.evidence_tracker.record_question_answer(
                session_token=self.session_token,
                question_id=question_id,
                selected_answer=selected_answer,
                is_correct=is_correct,
                time_spent_seconds=time_spent_seconds
            )
            logger.info(f"Recorded answer for question {question_id}")
        except Exception as e:
            logger.error(f"Failed to record question answer: {e}")

    def set_current_question(self, question_id: int) -> None:
        """Set the current question being answered."""
        self.current_question_id = question_id

    def get_session_summary(self) -> dict:
        """Get comprehensive proctoring summary for the session."""
        try:
            # Get all incidents
            incidents = self.evidence_tracker.get_session_incidents(self.session_token)

            # Get agent health
            agent_health = self.monitor.get_agent_health_report()

            # Get session risk score
            session = self._get_session()
            risk_score = getattr(session, "risk_score", 0) if session else 0
            risk_level = getattr(session, "proctoring_risk", "unknown") if session else "unknown"

            return {
                "session_token": self.session_token,
                "session_type": self.session_type,
                "total_incidents": len(incidents),
                "incidents": incidents,
                "risk_score": risk_score,
                "risk_level": risk_level,
                "agent_health": agent_health
            }

        except Exception as e:
            logger.error(f"Failed to get session summary: {e}")
            return {
                "session_token": self.session_token,
                "error": str(e)
            }

    def _get_session(self):
        """Get the session object based on session type."""
        try:
            if self.session_type == "mcq":
                return self.db.query(TestSession).filter(
                    TestSession.token == self.session_token
                ).first()
            elif self.session_type == "coding":
                return self.db.query(CodingSession).filter(
                    CodingSession.token == self.session_token
                ).first()
            elif self.session_type == "live_hr":
                return self.db.query(LiveSession).filter(
                    LiveSession.token == self.session_token
                ).first()
        except Exception as e:
            logger.error(f"Failed to get session: {e}")
        return None

    def _update_session_risk(self) -> None:
        """Update session risk score based on incidents."""
        try:
            session = self._get_session()
            if not session:
                return

            # Get all incidents
            incidents = self.evidence_tracker.get_session_incidents(self.session_token)

            # Calculate total risk
            total_risk = 0
            for incident in incidents:
                severity = incident.get("severity", "low")
                if severity == "critical":
                    total_risk += 10
                elif severity == "high":
                    total_risk += 5
                elif severity == "medium":
                    total_risk += 3
                else:
                    total_risk += 1

            # Update session
            session.risk_score = total_risk

            # Update risk level
            if total_risk >= 12:
                session.proctoring_risk = "severe"
                session.block_reason = "risk_threshold_reached"
            elif total_risk >= 9:
                session.proctoring_risk = "critical"
            elif total_risk >= 6:
                session.proctoring_risk = "high"
            elif total_risk >= 3:
                session.proctoring_risk = "medium"
            else:
                session.proctoring_risk = "low"

            self.db.commit()

        except Exception as e:
            logger.error(f"Failed to update session risk: {e}")
            self.db.rollback()


# Global session registry
_active_sessions = {}


def get_proctoring_session(
    session_token: str,
    session_type: str,
    db_session: Session
) -> EnhancedProctoringSession:
    """
    Get or create enhanced proctoring session.
    Maintains one session per token.
    """
    if session_token not in _active_sessions:
        _active_sessions[session_token] = EnhancedProctoringSession(
            session_token,
            session_type,
            db_session
        )
        logger.info(f"Created new proctoring session: {session_token}")

    return _active_sessions[session_token]


def close_proctoring_session(session_token: str) -> None:
    """Close and cleanup proctoring session."""
    if session_token in _active_sessions:
        del _active_sessions[session_token]
        logger.info(f"Closed proctoring session: {session_token}")
