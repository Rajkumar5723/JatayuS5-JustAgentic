"""
core/evidence_storage.py
=========================
Handles evidence file uploads to S3 and metadata storage.
"""
import asyncio
import io
import logging
import os
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from PIL import Image
from pydub import AudioSegment
from botocore.exceptions import ClientError

from core.config import settings
from core.s3_manager import S3CredentialsManager
from core.models import EvidenceFile

logger = logging.getLogger(__name__)

LOCAL_EVIDENCE_PREFIX = "local://"


def local_evidence_root() -> Path:
    return Path(__file__).resolve().parent.parent / "storage" / "evidence"


def local_evidence_public_url(storage_key: str) -> str:
    encoded = quote(storage_key, safe="")
    return f"{settings.public_main_api_url}/evidence/files?key={encoded}"


def resolve_local_evidence_path(storage_key: str) -> Optional[Path]:
    raw_key = str(storage_key or "")
    if not raw_key.startswith(LOCAL_EVIDENCE_PREFIX):
        return None
    relative = raw_key[len(LOCAL_EVIDENCE_PREFIX):].lstrip("/\\")
    target = (local_evidence_root() / relative).resolve()
    root = local_evidence_root().resolve()
    try:
        target.relative_to(root)
    except ValueError:
        return None
    return target


class EvidenceStorageService:
    """Handles evidence file uploads to S3 and metadata storage."""

    def __init__(self, credentials_manager: S3CredentialsManager, db_session):
        self.credentials_manager = credentials_manager
        self.db = db_session
        self.upload_queue: asyncio.Queue = asyncio.Queue(maxsize=100)
        self.queue_size_bytes: int = 0
        self.max_queue_size_bytes: int = 100 * 1024 * 1024  # 100MB
        self._queue_processor_task: Optional[asyncio.Task] = None

    def generate_s3_key(
        self,
        session_token: str,
        evidence_type: str,
        extension: str
    ) -> str:
        """Generate unique S3 key: {session_token}/{evidence_type}/{timestamp}_{uuid}.{ext}"""
        timestamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())
        return f"{session_token}/{evidence_type}/{timestamp}_{unique_id}.{extension}"

    def store_local_file(self, relative_key: str, file_data: bytes) -> Optional[str]:
        try:
            relative = str(relative_key or "").lstrip("/\\")
            target = (local_evidence_root() / relative).resolve()
            root = local_evidence_root().resolve()
            try:
                target.relative_to(root)
            except ValueError:
                logger.error("Rejected local evidence path outside root: %s", relative_key)
                return None
            target.parent.mkdir(parents=True, exist_ok=True)
            with open(target, "wb") as handle:
                handle.write(file_data)
            return f"{LOCAL_EVIDENCE_PREFIX}{relative.replace(os.sep, '/')}"
        except Exception as exc:
            logger.error("Failed to store local evidence file: %s", exc)
            return None

    async def compress_image(self, image_data: bytes) -> bytes:
        """Compress image to JPEG with 85% quality."""
        try:
            img = Image.open(io.BytesIO(image_data))
            # Convert RGBA to RGB if necessary
            if img.mode in ('RGBA', 'LA', 'P'):
                background = Image.new('RGB', img.size, (255, 255, 255))
                if img.mode == 'P':
                    img = img.convert('RGBA')
                background.paste(img, mask=img.split()[-1] if img.mode in ('RGBA', 'LA') else None)
                img = background

            output = io.BytesIO()
            img.save(output, format='JPEG', quality=85, optimize=True)
            compressed = output.getvalue()
            logger.info(f"Image compressed: {len(image_data)} -> {len(compressed)} bytes")
            return compressed
        except Exception as e:
            logger.error(f"Image compression failed: {e}, returning original")
            return image_data

    async def compress_audio(self, audio_data: bytes) -> bytes:
        """Compress audio to MP3 with 128kbps bitrate."""
        try:
            audio = AudioSegment.from_file(io.BytesIO(audio_data))
            output = io.BytesIO()
            audio.export(output, format='mp3', bitrate='128k')
            compressed = output.getvalue()
            logger.info(f"Audio compressed: {len(audio_data)} -> {len(compressed)} bytes")
            return compressed
        except Exception as e:
            logger.error(f"Audio compression failed: {e}, returning original")
            return audio_data

    async def upload_with_retry(
        self,
        s3_key: str,
        file_data: bytes,
        mime_type: str,
        max_retries: int = 3
    ) -> bool:
        """Upload to S3 with exponential backoff retry."""
        client = self.credentials_manager.get_client()
        bucket = self.credentials_manager.bucket_name

        for attempt in range(max_retries):
            try:
                client.put_object(
                    Bucket=bucket,
                    Key=s3_key,
                    Body=file_data,
                    ContentType=mime_type
                )
                logger.info(f"Successfully uploaded {s3_key} to S3 (attempt {attempt + 1})")
                return True
            except ClientError as e:
                error_code = e.response.get('Error', {}).get('Code', 'Unknown')
                logger.warning(f"S3 upload attempt {attempt + 1} failed: {error_code}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff: 1s, 2s, 4s
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"S3 upload failed after {max_retries} attempts: {s3_key}")
                    return False
            except Exception as e:
                logger.error(f"Unexpected error during S3 upload: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(2 ** attempt)
                else:
                    return False

        return False

    async def upload_evidence(
        self,
        session_token: str,
        evidence_type: str,  # "photo", "audio", "video"
        file_data: bytes,
        mime_type: str,
        metadata: dict
    ) -> Optional[str]:
        """
        Upload evidence to S3 and store metadata.
        Returns S3 key on success, None on failure.
        """
        start_time = time.time()

        # Compress based on type
        if evidence_type == "photo" and mime_type.startswith("image/"):
            file_data = await self.compress_image(file_data)
            mime_type = "image/jpeg"
            extension = "jpg"
        elif evidence_type == "audio" and mime_type.startswith("audio/"):
            file_data = await self.compress_audio(file_data)
            mime_type = "audio/mpeg"
            extension = "mp3"
        else:
            # Extract extension from mime type
            extension = mime_type.split('/')[-1] if '/' in mime_type else "bin"

        # Generate S3 key
        s3_key = self.generate_s3_key(session_token, evidence_type, extension)

        # Upload to S3
        upload_success = await self.upload_with_retry(s3_key, file_data, mime_type)
        storage_key = s3_key

        if not upload_success:
            storage_key = self.store_local_file(s3_key, file_data)
            if not storage_key:
                self.queue_for_upload({
                    'session_token': session_token,
                    'evidence_type': evidence_type,
                    'file_data': file_data,
                    'mime_type': mime_type,
                    's3_key': s3_key,
                    'metadata': metadata
                })
                return None
            logger.info("Stored evidence locally because S3 upload was unavailable: %s", storage_key)

        # Store metadata in database
        try:
            evidence_file = EvidenceFile(
                session_token=session_token,
                evidence_type=evidence_type,
                s3_key=storage_key,
                file_size_bytes=len(file_data),
                mime_type=mime_type
            )
            self.db.add(evidence_file)
            self.db.commit()
            self.db.refresh(evidence_file)

            elapsed = time.time() - start_time
            logger.info(f"Evidence uploaded and stored in {elapsed:.2f}s: {storage_key}")
            return storage_key

        except Exception as e:
            logger.error(f"Failed to store evidence metadata: {e}")
            self.db.rollback()
            return None

    def queue_for_upload(self, upload_task: dict) -> None:
        """Queue evidence for upload when network is unavailable."""
        file_size = len(upload_task['file_data'])

        # Check if adding this would exceed queue size
        if self.queue_size_bytes + file_size > self.max_queue_size_bytes:
            logger.warning(f"Upload queue full ({self.queue_size_bytes} bytes), discarding oldest evidence")
            # Try to remove oldest item
            try:
                oldest = self.upload_queue.get_nowait()
                self.queue_size_bytes -= len(oldest['file_data'])
            except asyncio.QueueEmpty:
                logger.error("Queue size exceeded but queue is empty - size tracking error")
                self.queue_size_bytes = 0

        try:
            self.upload_queue.put_nowait(upload_task)
            self.queue_size_bytes += file_size
            logger.info(f"Queued evidence for upload: {upload_task['s3_key']} (queue size: {self.queue_size_bytes} bytes)")
        except asyncio.QueueFull:
            logger.error("Upload queue full, cannot queue evidence")

    async def process_upload_queue(self) -> None:
        """Background task to process queued uploads."""
        logger.info("Starting upload queue processor")
        while True:
            try:
                # Wait for queued upload
                upload_task = await self.upload_queue.get()
                self.queue_size_bytes -= len(upload_task['file_data'])

                # Attempt upload
                success = await self.upload_with_retry(
                    upload_task['s3_key'],
                    upload_task['file_data'],
                    upload_task['mime_type']
                )

                if success:
                    # Store metadata
                    try:
                        evidence_file = EvidenceFile(
                            session_token=upload_task['session_token'],
                            evidence_type=upload_task['evidence_type'],
                            s3_key=upload_task['s3_key'],
                            file_size_bytes=len(upload_task['file_data']),
                            mime_type=upload_task['mime_type']
                        )
                        self.db.add(evidence_file)
                        self.db.commit()
                        logger.info(f"Queued evidence uploaded successfully: {upload_task['s3_key']}")
                    except Exception as e:
                        logger.error(f"Failed to store queued evidence metadata: {e}")
                        self.db.rollback()
                else:
                    logger.error(f"Failed to upload queued evidence: {upload_task['s3_key']}")

                self.upload_queue.task_done()

            except Exception as e:
                logger.error(f"Error in upload queue processor: {e}")
                await asyncio.sleep(5)

    def start_queue_processor(self) -> None:
        """Start the background queue processor."""
        if self._queue_processor_task is None or self._queue_processor_task.done():
            self._queue_processor_task = asyncio.create_task(self.process_upload_queue())
            logger.info("Upload queue processor started")

    def generate_presigned_url(self, s3_key: str, expiration: int = 3600) -> Optional[str]:
        """Generate presigned URL for evidence retrieval with 1-hour expiration."""
        try:
            if str(s3_key).startswith(LOCAL_EVIDENCE_PREFIX):
                return local_evidence_public_url(s3_key)
            client = self.credentials_manager.get_client()
            bucket = self.credentials_manager.bucket_name

            url = client.generate_presigned_url(
                'get_object',
                Params={'Bucket': bucket, 'Key': s3_key},
                ExpiresIn=expiration
            )
            logger.info(f"Generated presigned URL for {s3_key}")
            return url
        except Exception as e:
            logger.error(f"Failed to generate presigned URL for {s3_key}: {e}")
            return None
