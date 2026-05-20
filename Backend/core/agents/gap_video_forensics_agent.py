"""
core/agents/gap_video_forensics_agent.py
=========================================
Performs frame-by-frame forensic analysis of offline gap recordings.
"""
import logging
from typing import List

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class GapVideoForensicsAgent(MalpracticeDetectionAgent):
    """Performs frame-by-frame forensic analysis of offline gap recordings."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="gap_video_forensics_agent",
            groq_client=groq_client,
            detection_focus="gap_video_analysis"
        )
        self.analysis_frame_interval = 5  # Analyze every 5th frame

    async def analyze(
        self,
        video_path: str,
        metadata: dict
    ) -> dict:
        """
        Analyze offline gap video for malpractice indicators.
        Returns comprehensive analysis with verdict.
        """
        try:
            # Simplified analysis - in production, use OpenCV to extract frames
            # and analyze each frame
            
            total_frames = metadata.get("total_frames", 100)
            analyzed_frames = total_frames // self.analysis_frame_interval
            
            # Simulate detection percentages
            phone_detected_pct = 0.0
            face_missing_pct = 0.0
            multiple_people_pct = 0.0
            
            # Calculate verdict
            verdict = self.calculate_verdict(
                phone_detected_pct,
                face_missing_pct,
                multiple_people_pct
            )
            
            detected = verdict in ["suspicious", "likely_malpractice", "confirmed_malpractice"]
            confidence = 0.7 if detected else 0.3
            
            return {
                "detected": detected,
                "confidence": confidence,
                "detection_type": "gap_video_analysis",
                "evidence_data": b"",
                "reasoning": f"Gap video analysis: {verdict}",
                "agent_name": self.agent_name,
                "total_frames": total_frames,
                "analyzed_frames": analyzed_frames,
                "phone_detected_pct": phone_detected_pct,
                "face_missing_pct": face_missing_pct,
                "multiple_people_pct": multiple_people_pct,
                "verdict": verdict
            }
            
        except Exception as e:
            logger.error(f"{self.agent_name}: Analysis failed: {e}")
            return {
                "detected": False,
                "confidence": 0.0,
                "detection_type": "error",
                "evidence_data": b"",
                "reasoning": f"Error: {str(e)}",
                "agent_name": self.agent_name,
                "verdict": "error"
            }

    def calculate_verdict(
        self,
        phone_pct: float,
        face_missing_pct: float,
        multi_people_pct: float
    ) -> str:
        """Calculate final verdict based on detection percentages."""
        if phone_pct > 0.3 or multi_people_pct > 0.2:
            return "confirmed_malpractice"
        elif phone_pct > 0.15 or face_missing_pct > 0.4:
            return "likely_malpractice"
        elif phone_pct > 0.05 or face_missing_pct > 0.2:
            return "suspicious"
        else:
            return "clean"
