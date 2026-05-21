"""
core/config.py
==============
Single source of truth for all environment variables.
Every service imports `from core.config import settings`.

The root .env is located at  <repo_root>/.env
We walk up from this file's location to find it.
"""
from __future__ import annotations
import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


def _find_env() -> str:
    """Walk up directory tree until we find the root .env file."""
    here = os.path.dirname(os.path.abspath(__file__))
    candidate = here
    for _ in range(6):
        env_path = os.path.join(candidate, ".env")
        if os.path.exists(env_path):
            return env_path
        candidate = os.path.dirname(candidate)
    return ".env"  # fallback — let pydantic-settings look in cwd


_ENV_FILE = _find_env()
_REPO_ROOT = os.path.dirname(os.path.abspath(_ENV_FILE))


class Settings(BaseSettings):
    # ── Database ─────────────────────────────────────────────
    DATABASE_URL: str = ""
    AWS_DATABASE_URL: str = ""  # AWS RDS PostgreSQL URL
    DATABASE_MODE: str = "aws"  # local | aws | auto
    
    # ── AWS S3 Storage ───────────────────────────────────────
    AWS_ACCESS_KEY_ID: str = ""
    AWS_SECRET_ACCESS_KEY: str = ""
    AWS_REGION: str = "ap-south-1"
    AWS_S3_BUCKET: str = ""
    S3_EVIDENCE_BUCKET: str = ""  # For proctoring evidence

    # ── AI / GitHub ──────────────────────────────────────────
    GROQ_API_KEY: str = ""
    GITHUB_TOKEN: str = ""
    GROQ_MODEL: str = "llama-3.3-70b-versatile"
    GROQ_URL: str = "https://api.groq.com/openai/v1/chat/completions"
    GROQ_MODEL_VISION: str = "llama-3.2-90b-vision-preview"
    GROQ_MODEL_AUDIO: str = "whisper-large-v3"
    JAAS_APP_ID: str = ""

    # ── LinkedIn OAuth ────────────────────────────────────────
    LI_CLIENT_ID: str = ""
    LI_CLIENT_SECRET: str = ""
    LI_REDIRECT_URI: str = "http://localhost:8000/linkedin/callback"
    LI_SCOPE: str = "openid profile w_member_social"
    LI_EMAIL: str = ""
    LI_PASSWORD: str = ""

    # ── Email ─────────────────────────────────────────────────
    SMTP_USER: str = ""
    SMTP_PASS: str = ""
    SMTP_FROM: str = ""
    DISABLE_EMAIL_DELIVERY: bool = False

    # ── App ───────────────────────────────────────────────────
    FRONTEND_URL: str = "http://localhost:5173"
    PUBLIC_FRONTEND_URL: str = ""
    MAIN_API_URL: str = "http://127.0.0.1:8000"
    PUBLIC_MAIN_API_URL: str = ""
    EVAL_API_URL: str = ""
    TEST_API_URL: str = ""
    CODING_API_URL: str = ""
    LIVEHR_API_URL: str = ""
    SHORTLIST_MIN_SCORE: int = 40

    # ── Ports ─────────────────────────────────────────────────
    PORT_MAIN: int = 8000
    PORT_EVAL: int = 8001
    PORT_TEST: int = 8002
    PORT_CODING: int = 8003
    PORT_LIVEHR: int = 8004
    LIVEHR_ROOM_PREFIX: str = "hiresy"
    
    # ── Enhanced Proctoring ──────────────────────────────────
    QR_JWT_SECRET_KEY: str = "change-this-secret-key-in-production"
    CELERY_BROKER_URL: str = "redis://localhost:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://localhost:6379/0"

    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def smtp_from_addr(self) -> str:
        return self.SMTP_FROM or self.SMTP_USER

    def _normalize_sqlite_url(self, url: str) -> str:
        value = str(url or "").strip()
        if not value.startswith("sqlite:///./"):
            return value
        relative = value.removeprefix("sqlite:///./")
        absolute = os.path.abspath(os.path.join(_REPO_ROOT, relative))
        return f"sqlite:///{absolute.replace(os.sep, '/')}"
    
    @property
    def db_url(self) -> str:
        """Return the active database URL for the configured runtime mode."""
        mode = (self.DATABASE_MODE or "aws").strip().lower()
        local_url = self._normalize_sqlite_url(self.DATABASE_URL)
        aws_url = (self.AWS_DATABASE_URL or "").strip()
        if mode == "aws":
            if not aws_url:
                raise RuntimeError("DATABASE_MODE=aws requires AWS_DATABASE_URL to be set.")
            return aws_url
        if mode == "auto":
            return aws_url or local_url
        return local_url

    @property
    def public_frontend_url(self) -> str:
        return (self.PUBLIC_FRONTEND_URL or self.FRONTEND_URL).rstrip("/")

    def public_frontend_path(self, path: str = "") -> str:
        if not path:
            return self.public_frontend_url
        cleaned = str(path)
        if cleaned.startswith(("http://", "https://")):
            return cleaned
        if not cleaned.startswith("/"):
            cleaned = f"/{cleaned}"
        return f"{self.public_frontend_url}{cleaned}"

    @property
    def public_main_api_url(self) -> str:
        if self.PUBLIC_MAIN_API_URL:
            return self.PUBLIC_MAIN_API_URL.rstrip("/")
        return f"{self.public_frontend_url}/api"

    @property
    def eval_api_url(self) -> str:
        return (self.EVAL_API_URL or f"http://127.0.0.1:{self.PORT_EVAL}").rstrip("/")

    @property
    def test_api_url(self) -> str:
        return (self.TEST_API_URL or self._default_round_service_url(self.PORT_TEST)).rstrip("/")

    @property
    def coding_api_url(self) -> str:
        return (self.CODING_API_URL or self._default_round_service_url(self.PORT_CODING)).rstrip("/")

    @property
    def livehr_api_url(self) -> str:
        return (self.LIVEHR_API_URL or self._default_round_service_url(self.PORT_LIVEHR)).rstrip("/")

    def _default_round_service_url(self, port: int) -> str:
        main = (self.MAIN_API_URL or "").strip().rstrip("/")
        local_hosts = ("http://127.0.0.1", "http://localhost", "https://127.0.0.1", "https://localhost")
        if main and not main.startswith(local_hosts):
            return main
        return f"http://127.0.0.1:{port}"


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


# Convenience singleton
settings: Settings = get_settings()
