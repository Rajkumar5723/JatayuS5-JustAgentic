"""
core/agents/behavior_anomaly_agent.py
======================================
Detects unusual patterns in candidate behavior.
"""
import logging
from typing import List

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class BehaviorAnomalyAgent(MalpracticeDetectionAgent):
    """Detects unusual patterns in candidate behavior."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="behavior_anomaly_agent",
            groq_client=groq_client,
            detection_focus="behavior_anomalies"
        )
        self.baseline_metrics = {}

    async def analyze(
        self,
        session_events: List[dict],
        metadata: dict
    ) -> dict:
        """
        Analyze session events for behavioral anomalies.
        Returns detected anomalies and anomaly score.
        """
        try:
            anomalies = []
            
            # Detect rapid tab switches
            tab_anomalies = self.detect_rapid_tab_switches(session_events)
            anomalies.extend(tab_anomalies)
            
            # Detect timing anomalies
            timing_anomalies = self.detect_timing_anomalies(session_events)
            anomalies.extend(timing_anomalies)
            
            # Detect disconnect correlation
            disconnect_anomalies = self.detect_disconnect_correlation(session_events)
            anomalies.extend(disconnect_anomalies)
            
            # Calculate anomaly score
            anomaly_score = min(len(anomalies) * 0.2, 1.0)
            
            detected = len(anomalies) > 0
            confidence = anomaly_score
            
            return {
                "detected": detected,
                "confidence": confidence,
                "detection_type": "behavior_anomaly" if detected else "behavior_normal",
                "evidence_data": b"",
                "reasoning": f"Detected {len(anomalies)} behavioral anomalies",
                "agent_name": self.agent_name,
                "anomalies": anomalies,
                "anomaly_score": anomaly_score
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
                "anomalies": [],
                "anomaly_score": 0.0
            }

    def detect_rapid_tab_switches(
        self,
        events: List[dict]
    ) -> List[dict]:
        """Detect suspiciously rapid tab switching patterns."""
        anomalies = []
        
        tab_switches = [e for e in events if e.get("event_type") == "tab_hidden"]
        
        if len(tab_switches) >= 5:
            anomalies.append({
                "type": "rapid_tab_switching",
                "count": len(tab_switches),
                "severity": "high" if len(tab_switches) >= 10 else "medium"
            })
            
        return anomalies

    def detect_timing_anomalies(
        self,
        events: List[dict]
    ) -> List[dict]:
        """Detect unusual timing patterns."""
        anomalies = []
        
        # Check for answers that are too fast
        answer_events = [e for e in events if e.get("event_type") == "question_answered"]
        
        fast_answers = [e for e in answer_events if e.get("time_spent", 999) < 5]
        
        if len(fast_answers) >= 3:
            anomalies.append({
                "type": "suspiciously_fast_answers",
                "count": len(fast_answers),
                "severity": "medium"
            })
            
        return anomalies

    def detect_disconnect_correlation(
        self,
        events: List[dict]
    ) -> List[dict]:
        """Detect correlation between high-risk events and disconnects."""
        anomalies = []
        
        disconnects = [e for e in events if e.get("event_type") == "camera_error"]
        high_risk_events = [e for e in events if e.get("risk_delta", 0) >= 5]
        
        # Check if disconnects happen shortly after high-risk events
        correlated = 0
        for disconnect in disconnects:
            disconnect_time = disconnect.get("timestamp", 0)
            for risk_event in high_risk_events:
                risk_time = risk_event.get("timestamp", 0)
                if 0 < (disconnect_time - risk_time) < 30:  # Within 30 seconds
                    correlated += 1
                    break
                    
        if correlated >= 2:
            anomalies.append({
                "type": "disconnect_after_high_risk",
                "count": correlated,
                "severity": "high"
            })
            
        return anomalies
