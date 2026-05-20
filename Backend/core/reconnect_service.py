"""
core/reconnect_service.py
==========================
Validates reconnection attempts after network gaps.
"""
import logging
from datetime import datetime, timezone, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from core.models import ReconnectLog, CameraGap, TestSession, CodingSession, LiveSession
from core.agents import DeviceFingerprintAgent, DisconnectPatternAgent

logger = logging.getLogger(__name__)


class ReconnectService:
    """Validates reconnection attempts after network gaps."""

    def __init__(
        self,
        db_session: Session,
        device_fingerprint_agent: DeviceFingerprintAgent,
        disconnect_pattern_agent: DisconnectPatternAgent
    ):
        self.db = db_session
        self.device_fingerprint_agent = device_fingerprint_agent
        self.disconnect_pattern_agent = disconnect_pattern_agent
        self.max_gap_seconds = 600  # 10 minutes
        self.face_reverify_threshold = 30  # 30 seconds

    async def handle_reconnect(
        self,
        session_token: str,
        disconnect_timestamp: datetime,
        reconnect_timestamp: datetime,
        device_fingerprint_before: str,
        device_fingerprint_after: str,
        risk_score_before: float
    ) -> dict:
        """
        Validate reconnection attempt.
        Returns verdict and actions to take.
        """
        try:
            # Calculate gap duration
            gap_duration = (reconnect_timestamp - disconnect_timestamp).total_seconds()

            # Validate gap duration
            if gap_duration > self.max_gap_seconds:
                logger.warning(f"Gap duration exceeds maximum: {gap_duration}s")
                return {
                    "allowed": False,
                    "reason": "gap_too_long",
                    "action": "block_session",
                    "gap_duration": gap_duration
                }

            # Validate device fingerprint
            fingerprint_result = await self.device_fingerprint_agent.analyze(
                device_fingerprint_before,
                device_fingerprint_after,
                {"session_token": session_token}
            )

            # Analyze disconnect pattern
            disconnect_event = {
                "session_token": session_token,
                "gap_duration_seconds": gap_duration,
                "risk_score_before": risk_score_before,
                "disconnect_count": self._get_disconnect_count(session_token),
                "disconnect_timestamp": disconnect_timestamp.isoformat()
            }

            pattern_result = await self.disconnect_pattern_agent.analyze(
                disconnect_event,
                {"session_token": session_token}
            )

            # Calculate risk penalty
            risk_penalty = self.calculate_gap_penalty(
                gap_duration,
                fingerprint_result,
                pattern_result
            )

            # Create reconnect log
            reconnect_log = ReconnectLog(
                session_token=session_token,
                disconnect_timestamp=disconnect_timestamp,
                reconnect_timestamp=reconnect_timestamp,
                gap_duration_seconds=int(gap_duration),
                device_fingerprint_before=device_fingerprint_before,
                device_fingerprint_after=device_fingerprint_after,
                fingerprint_match=fingerprint_result.get("fingerprint_match", True),
                disconnect_verdict=pattern_result.get("verdict", "clean"),
                risk_penalty=risk_penalty,
                analysis_completed=False
            )
            self.db.add(reconnect_log)
            self.db.flush()

            # Create camera gap record
            camera_gap = CameraGap(
                session_token=session_token,
                reconnect_log_id=reconnect_log.id,
                gap_start=disconnect_timestamp,
                gap_end=reconnect_timestamp,
                gap_duration_seconds=int(gap_duration)
            )
            self.db.add(camera_gap)

            # Apply risk penalty
            self._apply_risk_penalty(session_token, risk_penalty)

            self.db.commit()

            # Determine actions
            actions = []
            if gap_duration > self.face_reverify_threshold:
                actions.append("require_face_reverification")

            if pattern_result.get("verdict") in ["likely_malpractice", "confirmed_malpractice"]:
                actions.append("flag_for_review")

            if fingerprint_result.get("risk_level") == "critical":
                actions.append("block_session")
                allowed = False
            else:
                allowed = True

            logger.info(f"Reconnect handled for {session_token}: gap={gap_duration}s, penalty={risk_penalty}")

            return {
                "allowed": allowed,
                "gap_duration": gap_duration,
                "risk_penalty": risk_penalty,
                "fingerprint_match": fingerprint_result.get("fingerprint_match"),
                "disconnect_verdict": pattern_result.get("verdict"),
                "actions": actions,
                "reconnect_log_id": reconnect_log.id,
                "camera_gap_id": camera_gap.id
            }

        except Exception as e:
            logger.error(f"Reconnect handling failed: {e}")
            self.db.rollback()
            return {
                "allowed": False,
                "reason": "error",
                "error": str(e)
            }

    def calculate_gap_penalty(
        self,
        gap_duration: float,
        fingerprint_result: dict,
        pattern_result: dict
    ) -> int:
        """Calculate risk penalty based on gap analysis."""
        penalty = 0

        # Base penalty for gap duration
        if gap_duration > 300:  # > 5 minutes
            penalty += 8
        elif gap_duration > 120:  # > 2 minutes
            penalty += 5
        elif gap_duration > 60:  # > 1 minute
            penalty += 3
        elif gap_duration > 30:  # > 30 seconds
            penalty += 2

        # Fingerprint mismatch penalty
        if not fingerprint_result.get("fingerprint_match"):
            penalty += 5

        # Pattern analysis penalty
        pattern_penalty = pattern_result.get("penalty", 0)
        penalty += pattern_penalty

        return penalty

    def _get_disconnect_count(self, session_token: str) -> int:
        """Get number of previous disconnects for this session."""
        count = self.db.query(ReconnectLog).filter(
            ReconnectLog.session_token == session_token
        ).count()
        return count

    def _apply_risk_penalty(self, session_token: str, penalty: int) -> None:
        """Apply risk penalty to session."""
        try:
            for session_model in [TestSession, CodingSession, LiveSession]:
                session = self.db.query(session_model).filter(
                    session_model.token == session_token
                ).first()

                if session:
                    current_risk = getattr(session, "risk_score", 0) or 0
                    session.risk_score = current_risk + penalty

                    # Update risk level
                    if session.risk_score >= 12:
                        session.proctoring_risk = "severe"
                        session.block_reason = "risk_threshold_reached"
                    elif session.risk_score >= 9:
                        session.proctoring_risk = "critical"
                    elif session.risk_score >= 6:
                        session.proctoring_risk = "high"

                    break

        except Exception as e:
            logger.error(f"Failed to apply risk penalty: {e}")

    async def queue_gap_analysis(
        self,
        camera_gap_id: int,
        offline_recording_s3_key: str
    ) -> None:
        """Queue gap video for asynchronous analysis."""
        try:
            # Update camera gap with recording
            camera_gap = self.db.query(CameraGap).filter(
                CameraGap.id == camera_gap_id
            ).first()

            if camera_gap:
                camera_gap.offline_recording_s3_key = offline_recording_s3_key
                self.db.commit()

                # In production, queue Celery task here
                logger.info(f"Queued gap analysis for camera_gap_id={camera_gap_id}")

        except Exception as e:
            logger.error(f"Failed to queue gap analysis: {e}")
            self.db.rollback()
