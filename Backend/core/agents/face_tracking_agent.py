"""
core/agents/face_tracking_agent.py
===================================
Monitors face continuity and presence.
"""
import base64
import logging
from typing import Optional
import numpy as np

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class FaceTrackingAgent(MalpracticeDetectionAgent):
    """Monitors face continuity and presence."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="face_tracking_agent",
            groq_client=groq_client,
            detection_focus="face_continuity"
        )
        self.reference_face_embedding: Optional[np.ndarray] = None
        self.reference_face_b64: Optional[str] = None

    def set_reference_face(self, face_data: str) -> None:
        """Set reference face for continuity checking."""
        self.reference_face_b64 = face_data
        logger.info(f"{self.agent_name}: Reference face set")

    async def analyze(
        self,
        frame_data: bytes,
        metadata: dict
    ) -> dict:
        """
        Detect face presence and compare with reference face.
        Returns detection result with similarity score.
        """
        try:
            # Convert frame to base64
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')

            # If no reference face, just check for face presence
            if not self.reference_face_b64:
                prompt = """Analyze this image and determine:
1. Is there a human face clearly visible?
2. Is the face looking at the camera?
3. Are there multiple faces?

Respond in JSON format:
{
  "face_detected": true/false,
  "face_count": number,
  "looking_at_camera": true/false,
  "confidence": 0.0-1.0
}"""
                
                result = await self.call_groq_api(prompt, timeout_seconds=2)
                
                if result.get("success"):
                    import json
                    try:
                        analysis = json.loads(result["content"])
                        detected = not analysis.get("face_detected", True) or analysis.get("face_count", 1) > 1
                        
                        return {
                            "detected": detected,
                            "confidence": analysis.get("confidence", 0.5),
                            "detection_type": "no_face" if not analysis.get("face_detected") else "multiple_faces",
                            "evidence_data": frame_data,
                            "reasoning": f"Face detected: {analysis.get('face_detected')}, Count: {analysis.get('face_count')}",
                            "agent_name": self.agent_name
                        }
                    except:
                        pass

            # Compare with reference face
            prompt = f"""Compare these two face images and determine if they are the same person.
Consider lighting, angle, and facial features.

Respond in JSON format:
{{
  "same_person": true/false,
  "similarity_score": 0.0-1.0,
  "confidence": 0.0-1.0,
  "reason": "brief explanation"
}}"""

            result = await self.call_groq_api(prompt, timeout_seconds=2)
            
            if result.get("success"):
                import json
                try:
                    analysis = json.loads(result["content"])
                    similarity = analysis.get("similarity_score", 0.8)
                    same_person = analysis.get("same_person", True)
                    
                    # Flag if similarity is low
                    detected = not same_person or similarity < 0.6
                    
                    return {
                        "detected": detected,
                        "confidence": analysis.get("confidence", 0.7),
                        "detection_type": "face_mismatch" if detected else "face_match",
                        "evidence_data": frame_data,
                        "reasoning": analysis.get("reason", "Face comparison completed"),
                        "agent_name": self.agent_name,
                        "similarity_score": similarity
                    }
                except Exception as e:
                    logger.error(f"Failed to parse Groq response: {e}")

            # Default: no detection
            return {
                "detected": False,
                "confidence": 0.5,
                "detection_type": "face_check",
                "evidence_data": frame_data,
                "reasoning": "Face tracking completed",
                "agent_name": self.agent_name
            }

        except Exception as e:
            logger.error(f"{self.agent_name}: Analysis failed: {e}")
            return {
                "detected": False,
                "confidence": 0.0,
                "detection_type": "error",
                "evidence_data": b"",
                "reasoning": f"Error: {str(e)}",
                "agent_name": self.agent_name
            }
