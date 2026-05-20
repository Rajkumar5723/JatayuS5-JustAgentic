"""
core/s3_manager.py
==================
Manages AWS S3 credentials and connection pooling for evidence storage.
"""
import os
import logging
from typing import Optional
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError, NoCredentialsError

from core.config import settings

logger = logging.getLogger(__name__)


class S3CredentialsManager:
    """Manages AWS S3 credentials and connection pooling."""

    def __init__(self):
        self.access_key_id: Optional[str] = None
        self.secret_access_key: Optional[str] = None
        self.session_token: Optional[str] = None
        self.bucket_name: Optional[str] = None
        self.region: str = "us-east-1"
        self.client: Optional[boto3.client] = None
        self.connection_pool_size: int = 5
        self.load_credentials_from_env()

    def load_credentials_from_env(self) -> None:
        """Load credentials from environment variables."""
        self.access_key_id = settings.AWS_ACCESS_KEY_ID
        self.secret_access_key = settings.AWS_SECRET_ACCESS_KEY
        self.session_token = os.getenv("AWS_SESSION_TOKEN")
        self.bucket_name = settings.AWS_S3_BUCKET or settings.S3_EVIDENCE_BUCKET
        self.region = settings.AWS_REGION or "us-east-1"

        if not self.access_key_id or not self.secret_access_key:
            logger.warning("AWS credentials not found in environment variables")
            return

        if not self.bucket_name:
            logger.warning("S3 bucket name not found in environment variables")
            return

        # Create client with connection pooling
        config = Config(
            region_name=self.region,
            max_pool_connections=self.connection_pool_size,
            retries={'max_attempts': 3, 'mode': 'standard'}
        )

        session_kwargs = {
            'aws_access_key_id': self.access_key_id,
            'aws_secret_access_key': self.secret_access_key,
            'region_name': self.region,
            'config': config
        }

        if self.session_token:
            session_kwargs['aws_session_token'] = self.session_token
            logger.info("Using temporary AWS credentials with session token")
        else:
            logger.info("Using permanent AWS credentials")

        try:
            self.client = boto3.client('s3', **session_kwargs)
            logger.info(f"S3 client initialized for bucket: {self.bucket_name}, region: {self.region}")
        except Exception as e:
            logger.error(f"Failed to create S3 client: {e}")
            self.client = None

    def validate_credentials(self) -> bool:
        """Validate credentials by attempting a list operation."""
        if not self.client or not self.bucket_name:
            logger.error("S3 client or bucket name not configured")
            return False

        try:
            # Try to list objects with max 1 result to test credentials
            self.client.list_objects_v2(Bucket=self.bucket_name, MaxKeys=1)
            logger.info("S3 credentials validated successfully")
            return True
        except NoCredentialsError:
            logger.error("AWS credentials not found or invalid")
            return False
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', 'Unknown')
            logger.error(f"S3 credential validation failed: {error_code} - {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error during S3 validation: {e}")
            return False

    def get_client(self) -> boto3.client:
        """Get S3 client with connection pooling."""
        if not self.client:
            logger.warning("S3 client not initialized, attempting to reload credentials")
            self.load_credentials_from_env()

        if not self.client:
            raise RuntimeError("S3 client not available. Check AWS credentials configuration.")

        return self.client

    def rotate_credentials(self) -> None:
        """Re-read environment variables and recreate client."""
        logger.info("Rotating AWS credentials")
        self.load_credentials_from_env()
        if self.client and self.validate_credentials():
            logger.info("Credentials rotated successfully")
        else:
            logger.error("Failed to rotate credentials")


# Global instance
_s3_manager: Optional[S3CredentialsManager] = None


def get_s3_manager() -> S3CredentialsManager:
    """Get or create global S3 credentials manager instance."""
    global _s3_manager
    if _s3_manager is None:
        _s3_manager = S3CredentialsManager()
    return _s3_manager
