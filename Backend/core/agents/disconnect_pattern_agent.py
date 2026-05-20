"""
core/agents/disconnect_pattern_agent.py
========================================
Analyzes disconnect patterns to detect intentional disconnections.
"""
import logging
from typing import List
from datetime import datetime

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class DisconnectPatternAgent(MalpracticeDetectionAgent):
    """Analyzes disconnect patterns to detect intentional disconnections."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="disconnect_pattern_agent",
            groq_client=groq_client,
            detection_focus="disconnect_patterns"
        )
        self.pattern_thresholds = {
            "short_gap_threshold": 5,  # seconds
            "risk_spike_threshold": 6.0,
            "long_gap_threshold": 120,  # seconds
        }

    async def analyze(
        self,
        disconnect_event: dict,
        metadata: dict
    ) -> dict:
        """
        Analyze disconnect event for intentional patterns.
        Returns verdict and penalty.
        """
        try:
            gap_seconds = disconnect_event.get("gap_duration_seconds", 0)
            risk_score_before = disconnect_event.get("risk_score_before", 0)
            disconnect_count = disconnect_event.get("disconnect_count", 1)
            
            flags = []
            penalty = 0
            
            # Check timing patterns
            timing_flags = self.check_timing_patterns(
                disconnect_event.get("disconnect_timestamp"),
                risk_score_before,
                gap_seconds
            )
            flags.extend(timing_flags)
            
            # Check frequency patterns
            frequency_flags = self.check_frequency_patterns(
                disconnect_event.get("session_token"),
                disconnect_count
            )
            flags.extend(frequency_flags)
            
            # Calculate penalty and verdict
            if "risk_spike_before_disconnect" in flags:
                penalty += 5
            if "long_gap" in flags:
                penalty += 3
            if "repeated_disconnects" in flags:
                penalty += 4
            if "suspicious_timing" in flags:
                penalty += 3
                
            # Determine verdict
            if penalty >= 10:
                verdict = "confirmed_malpractice"
                confidence = 0.9
            elif penalty >= 7:
                verdict = "likely_malpractice"
                confidence = 0.75
            elif penalty >= 4:
                verdict = "suspicious"
                confidence = 0.6
            else:
                verdict = "clean"
                confidence = 0.3
                
            detected = verdict in ["suspicious", "likely_malpractice", "confirmed_malpractice"]
            
            return {
                "detected": detected,
                "confidence": confidence,
                "detection_type": "disconnect_pattern",
                "evidence_data": b"",
                "reasoning": f"Disconnect analysis: {verdict}, flags: {', '.join(flags)}",
                "agent_name": self.agent_name,
                "flags": flags,
                "penalty": penalty,
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
                "flags": [],
                "penalty": 0,
                "verdict": "error"
            }

    def check_timing_patterns(
        self,
        disconnect_ts: str,
        risk_score: float,
        gap_seconds: float
    ) -> List[str]:
        """Check for suspicious timing patterns."""
        flags = []
        
        # Check if risk score was high before disconnect
        if risk_score >= self.pattern_thresholds["risk_spike_threshold"]:
            flags.append("risk_spike_before_disconnect")
            
        # Check gap duration
        if gap_seconds > self.pattern_thresholds["long_gap_threshold"]:
            flags.append("long_gap")
        elif gap_seconds < self.pattern_thresholds["short_gap_threshold"]:
            flags.append("very_short_gap")
            
        return flags

    def check_frequency_patterns(
        self,
        session_id: str,
        disconnect_count: int
    ) -> List[str]:
        """Check for repeated disconnect patterns."""
        flags = []
        
        if disconnect_count >= 3:
            flags.append("repeated_disconnects")
        elif disconnect_count >= 2:
            flags.append("multiple_disconnects")
            
        return flags
