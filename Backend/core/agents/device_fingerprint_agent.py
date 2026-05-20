"""
core/agents/device_fingerprint_agent.py
========================================
Validates device consistency across reconnections.
"""
import logging
from typing import List

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class DeviceFingerprintAgent(MalpracticeDetectionAgent):
    """Validates device consistency across reconnections."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="device_fingerprint_agent",
            groq_client=groq_client,
            detection_focus="device_consistency"
        )

    async def analyze(
        self,
        fingerprint_before: str,
        fingerprint_after: str,
        metadata: dict
    ) -> dict:
        """
        Compare device fingerprints before and after disconnect.
        Returns match status and changed components.
        """
        try:
            fp_before = self.parse_fingerprint(fingerprint_before)
            fp_after = self.parse_fingerprint(fingerprint_after)
            
            changed_components = self.compare_components(fp_before, fp_after)
            
            fingerprint_match = len(changed_components) == 0
            
            # Determine risk level
            if len(changed_components) >= 3:
                risk_level = "critical"
                confidence = 0.9
            elif len(changed_components) >= 2:
                risk_level = "high"
                confidence = 0.75
            elif len(changed_components) == 1:
                risk_level = "medium"
                confidence = 0.6
            else:
                risk_level = "low"
                confidence = 0.2
                
            detected = not fingerprint_match
            
            return {
                "detected": detected,
                "confidence": confidence,
                "detection_type": "device_change" if detected else "device_match",
                "evidence_data": b"",
                "reasoning": f"Device fingerprint {'mismatch' if detected else 'match'}: {', '.join(changed_components) if changed_components else 'all components match'}",
                "agent_name": self.agent_name,
                "fingerprint_match": fingerprint_match,
                "changed_components": changed_components,
                "risk_level": risk_level
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
                "fingerprint_match": True,
                "changed_components": [],
                "risk_level": "unknown"
            }

    def parse_fingerprint(self, fingerprint: str) -> dict:
        """Parse fingerprint string into components."""
        # Expected format: "browser|os|screen|timezone|language|..."
        parts = fingerprint.split("|") if fingerprint else []
        return {
            "browser": parts[0] if len(parts) > 0 else "",
            "os": parts[1] if len(parts) > 1 else "",
            "screen": parts[2] if len(parts) > 2 else "",
            "timezone": parts[3] if len(parts) > 3 else "",
            "language": parts[4] if len(parts) > 4 else "",
        }

    def compare_components(
        self,
        fp_before: dict,
        fp_after: dict
    ) -> List[str]:
        """Identify which fingerprint components changed."""
        changed = []
        
        for key in fp_before.keys():
            if fp_before.get(key) != fp_after.get(key):
                changed.append(key)
                
        return changed
