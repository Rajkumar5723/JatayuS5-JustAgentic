"""
core/agents/audio_analysis_agent.py
====================================
Transcribes and analyzes audio for suspicious patterns.
"""
import logging
import json

from .base_agent import MalpracticeDetectionAgent

logger = logging.getLogger(__name__)


class AudioAnalysisAgent(MalpracticeDetectionAgent):
    """Transcribes and analyzes audio for suspicious patterns."""

    def __init__(self, groq_client):
        super().__init__(
            agent_name="audio_analysis_agent",
            groq_client=groq_client,
            detection_focus="audio_anomalies"
        )
        self.suspicious_patterns = [
            "multiple_voices", "phone_ringing", "keyboard_typing",
            "conversation", "background_voices", "notification_sounds"
        ]

    async def analyze(
        self,
        audio_data: bytes,
        metadata: dict
    ) -> dict:
        """
        Transcribe audio and detect suspicious patterns.
        Returns detection result with transcript and pattern matches.
        """
        try:
            # For now, use a simplified analysis
            # In production, you would use Groq's audio transcription API
            
            prompt = """Analyze this audio clip for suspicious patterns that might indicate cheating:
- Multiple voices (conversation)
- Phone ringing or notification sounds
- Keyboard typing sounds
- Background voices or talking
- Any other suspicious audio

Respond in JSON format:
{
  "patterns_detected": ["pattern1", "pattern2"],
  "transcript": "any speech detected",
  "suspicious": true/false,
  "confidence": 0.0-1.0,
  "reasoning": "brief explanation"
}"""

            result = await self.call_groq_api(prompt, timeout_seconds=3)

            if result.get("success"):
                try:
                    analysis = json.loads(result["content"])
                    patterns = analysis.get("patterns_detected", [])
                    suspicious = analysis.get("suspicious", False)
                    
                    detected = suspicious and len(patterns) > 0

                    return {
                        "detected": detected,
                        "confidence": analysis.get("confidence", 0.5),
                        "detection_type": "audio_anomaly" if detected else "audio_clean",
                        "evidence_data": audio_data,
                        "reasoning": analysis.get("reasoning", "Audio analysis completed"),
                        "agent_name": self.agent_name,
                        "patterns": patterns,
                        "transcript": analysis.get("transcript", "")
                    }
                except Exception as e:
                    logger.error(f"Failed to parse Groq response: {e}")

            # Default: no detection
            return {
                "detected": False,
                "confidence": 0.5,
                "detection_type": "audio_check",
                "evidence_data": audio_data,
                "reasoning": "Audio analysis completed",
                "agent_name": self.agent_name,
                "patterns": [],
                "transcript": ""
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
                "patterns": [],
                "transcript": ""
            }
