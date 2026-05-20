"""
core/qr_verification.py
========================
Generates QR codes and manages 360-degree verification.
"""
import os
import logging
import base64
import io
from datetime import datetime, timedelta, timezone
from typing import Optional

import qrcode
import jwt

from core.config import settings

logger = logging.getLogger(__name__)


class QRVerificationService:
    """Generates QR codes and manages 360-degree verification."""

    def __init__(self, secret_key: Optional[str] = None):
        self.secret_key = secret_key or settings.QR_JWT_SECRET_KEY
        self.jwt_expiration_minutes: int = 15
        self.domain = settings.public_frontend_url

    def create_jwt_token(
        self,
        session_token: str,
        verification_type: str
    ) -> str:
        """Create signed JWT token with expiration."""
        payload = {
            'session_token': session_token,
            'verification_type': verification_type,
            'timestamp': datetime.now(timezone.utc).isoformat(),
            'exp': datetime.now(timezone.utc) + timedelta(minutes=self.jwt_expiration_minutes)
        }
        token = jwt.encode(payload, self.secret_key, algorithm='HS256')
        logger.info(f"Created JWT token for session {session_token}, type: {verification_type}")
        return token

    def build_verification_url(self, token: str) -> str:
        """Build the frontend URL opened after scanning a QR code."""
        return settings.public_frontend_path(f"/verify/360?token={token}")

    def validate_jwt_token(self, token: str) -> dict:
        """
        Validate JWT token signature and expiration.
        Returns decoded payload or raises exception.
        """
        try:
            payload = jwt.decode(token, self.secret_key, algorithms=['HS256'])
            logger.info(f"JWT token validated for session {payload.get('session_token')}")
            return payload
        except jwt.ExpiredSignatureError:
            logger.warning("JWT token expired")
            raise ValueError("JWT_EXPIRED")
        except jwt.InvalidSignatureError:
            logger.error("JWT token has invalid signature")
            raise ValueError("JWT_INVALID_SIGNATURE")
        except jwt.DecodeError:
            logger.error("JWT token is malformed")
            raise ValueError("JWT_MALFORMED")
        except Exception as e:
            logger.error(f"JWT validation error: {e}")
            raise ValueError("JWT_VALIDATION_ERROR")

    def generate_qr_code(
        self,
        session_token: str,
        verification_type: str = "initial",  # "initial" or "re-verification"
        token: Optional[str] = None,
    ) -> str:
        """
        Generate QR code with signed JWT token.
        Returns base64-encoded PNG image.
        """
        try:
            # Create JWT token
            token = token or self.create_jwt_token(session_token, verification_type)

            # Create verification URL
            verification_url = self.build_verification_url(token)

            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(verification_url)
            qr.make(fit=True)

            # Create image
            img = qr.make_image(fill_color="black", back_color="white")

            # Convert to base64
            buffer = io.BytesIO()
            img.save(buffer, format='PNG')
            img_bytes = buffer.getvalue()
            img_base64 = base64.b64encode(img_bytes).decode('utf-8')

            logger.info(f"Generated QR code for session {session_token}")
            return f"data:image/png;base64,{img_base64}"

        except Exception as e:
            logger.error(f"Failed to generate QR code: {e}")
            raise

    def create_mobile_camera_session(
        self,
        session_token: str,
        verification_type: str
    ) -> str:
        """
        Create mobile camera session linked to test session.
        Returns mobile session ID.
        """
        import uuid
        mobile_session_id = f"mobile_{session_token}_{uuid.uuid4().hex[:8]}"
        logger.info(f"Created mobile camera session: {mobile_session_id} for {session_token}")
        return mobile_session_id
