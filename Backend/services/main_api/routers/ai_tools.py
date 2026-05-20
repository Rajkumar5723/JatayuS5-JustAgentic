"""
services/main_api/routers/ai_tools.py
========================================
AI utility endpoints:
  POST /ai/spellcheck  — grammar & spelling correction via Groq
"""
from __future__ import annotations
import json
import logging
import sys, os

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import requests
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from core.config import settings

router = APIRouter(prefix="/ai", tags=["ai-tools"])
logger = logging.getLogger(__name__)


class SpellCheckRequest(BaseModel):
    text: str


@router.post("/spellcheck")
def spellcheck(req: SpellCheckRequest):
    """Fix spelling and grammar in a job description using Groq AI."""
    if not req.text.strip():
        raise HTTPException(400, "Text is empty")
    if not settings.GROQ_API_KEY:
        raise HTTPException(503, "AI service not configured")

    prompt = (
        "You are a professional copy editor. Fix ALL spelling mistakes, grammar errors, "
        "and improve sentence clarity in the following job description. "
        "Keep the original meaning, tone, and structure intact. "
        "Do NOT add or remove bullet points or sections. "
        "Return ONLY the corrected text — no explanations, no markdown, no JSON.\n\n"
        f"TEXT:\n{req.text}"
    )

    try:
        res = requests.post(
            settings.GROQ_URL,
            json={
                "model": settings.GROQ_MODEL,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.2,
                "max_tokens": 2000,
            },
            headers={
                "Authorization": f"Bearer {settings.GROQ_API_KEY}",
                "Content-Type": "application/json",
            },
            timeout=30,
        )
        if not res.ok:
            error_data = res.json() if res.content else {"error": res.text}
            logger.error("Groq API error: %s", error_data)
            raise HTTPException(res.status_code, f"Groq API error: {error_data}")
            
        corrected = res.json()["choices"][0]["message"]["content"].strip()
        return {"corrected": corrected, "original": req.text}
    except requests.RequestException as exc:
        logger.error("Network error calling Groq: %s", exc)
        raise HTTPException(502, f"Network error calling AI service: {exc}")
    except Exception as exc:
        logger.error("Unexpected error in spellcheck: %s", exc)
        raise HTTPException(500, f"Internal error: {exc}")
