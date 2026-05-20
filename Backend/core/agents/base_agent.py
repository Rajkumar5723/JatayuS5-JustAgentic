"""
core/agents/base_agent.py
==========================
Base class for specialized malpractice detection agents.
"""
import os
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Any

from groq import Groq

logger = logging.getLogger(__name__)


class MalpracticeDetectionAgent(ABC):
    """Base class for specialized malpractice detection agents."""

    def __init__(
        self,
        agent_name: str,
        groq_client: Optional[Groq],
        detection_focus: str
    ):
        self.agent_name = agent_name
        self.groq_client = groq_client
        self.detection_focus = detection_focus
        self.use_local_fallback: bool = True
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        
        # Initialize Groq client if not provided
        if not self.groq_client and self.groq_api_key:
            self.groq_client = Groq(api_key=self.groq_api_key)

    @abstractmethod
    async def analyze(
        self,
        data: bytes,
        metadata: dict
    ) -> dict:
        """
        Analyze input data and return detection result.
        Returns: {
            "detected": bool,
            "confidence": float,
            "detection_type": str,
            "evidence_data": bytes,
            "reasoning": str,
            "agent_name": str
        }
        """
        pass

    async def call_groq_api(
        self,
        prompt: str,
        timeout_seconds: int,
        model: Optional[str] = None
    ) -> dict:
        """Call Groq API with timeout and error handling."""
        if not self.groq_client:
            logger.warning(f"{self.agent_name}: Groq client not available, using fallback")
            return await self.fallback_to_local({})

        try:
            # Use asyncio timeout
            async def _call():
                response = self.groq_client.chat.completions.create(
                    model=model or os.getenv("GROQ_MODEL_VISION", "llama-3.2-90b-vision-preview"),
                    messages=[
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    temperature=0.1,
                    max_tokens=1024
                )
                return response

            response = await asyncio.wait_for(_call(), timeout=timeout_seconds)
            
            content = response.choices[0].message.content
            logger.info(f"{self.agent_name}: Groq API call successful")
            
            return {
                "success": True,
                "content": content,
                "model": response.model,
                "usage": response.usage.total_tokens if hasattr(response, 'usage') else 0
            }

        except asyncio.TimeoutError:
            logger.warning(f"{self.agent_name}: Groq API timeout after {timeout_seconds}s")
            if self.use_local_fallback:
                return await self.fallback_to_local({})
            return {"success": False, "error": "AGENT_TIMEOUT"}

        except Exception as e:
            logger.error(f"{self.agent_name}: Groq API error: {e}")
            if self.use_local_fallback:
                return await self.fallback_to_local({})
            return {"success": False, "error": "AGENT_API_ERROR"}

    async def fallback_to_local(
        self,
        data: dict
    ) -> dict:
        """Fallback to local inference model."""
        logger.info(f"{self.agent_name}: Using local fallback")
        # Default fallback returns no detection
        return {
            "success": True,
            "content": "No detection (local fallback)",
            "fallback": True
        }
