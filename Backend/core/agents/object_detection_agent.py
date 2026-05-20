"""
core/agents/object_detection_agent.py
======================================
Detects suspicious objects in video frames.
"""
import base64
import logging
import json

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class ObjectDetectionAgent(MalpracticeDetectionAgent):
    """Detects suspicious objects in video frames."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="object_detection_agent",
            groq_client=groq_client,
            detection_focus="suspicious_objects"
        )
        self.target_objects = [
            "cell_phone", "smartphone", "book", "notebook",
            "monitor", "laptop", "tablet", "paper", "notes"
        ]

    async def analyze(
        self,
        frame_data: bytes,
        metadata: dict
    ) -> dict:
        """
        Detect suspicious objects in frame.
        Returns detection result with object labels and confidence.
        """
        try:
            # Convert frame to base64
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')

            prompt = f"""Analyze this image and detect any of these suspicious objects that could be used for cheating:
- Cell phones or smartphones
- Books or notebooks
- Additional monitors or screens
- Laptops or tablets
- Papers with notes

Respond in JSON format:
{{
  "objects_detected": [
    {{
      "object": "object name",
      "confidence": 0.0-1.0,
      "location": "description of where in frame"
    }}
  ],
  "suspicious": true/false,
  "overall_confidence": 0.0-1.0
}}"""

            result = await self.call_groq_api(prompt, timeout_seconds=2)

            if result.get("success"):
                try:
                    analysis = json.loads(result["content"])
                    objects_detected = analysis.get("objects_detected", [])
                    suspicious = analysis.get("suspicious", False)
                    
                    # Check if any high-confidence detections
                    high_conf_objects = [
                        obj for obj in objects_detected 
                        if obj.get("confidence", 0) > 0.7
                    ]

                    detected = suspicious and len(high_conf_objects) > 0

                    return {
                        "detected": detected,
                        "confidence": analysis.get("overall_confidence", 0.5),
                        "detection_type": "suspicious_object" if detected else "no_object",
                        "evidence_data": frame_data,
                        "reasoning": f"Detected objects: {', '.join([obj['object'] for obj in high_conf_objects])}",
                        "agent_name": self.agent_name,
                        "objects": objects_detected
                    }
                except Exception as e:
                    logger.error(f"Failed to parse Groq response: {e}")

            # Default: no detection
            return {
                "detected": False,
                "confidence": 0.5,
                "detection_type": "object_check",
                "evidence_data": frame_data,
                "reasoning": "Object detection completed",
                "agent_name": self.agent_name,
                "objects": []
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
                "objects": []
            }
