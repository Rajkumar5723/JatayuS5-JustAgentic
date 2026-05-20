"""
core/room_scan_analyzer.py
===========================
Analyzes 360-degree room scans for suspicious items.
"""
import logging
import json
import base64
from typing import List, Optional
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from core.models import RoomScan, RoomScanFrame, EvidenceFile
from core.evidence_storage import EvidenceStorageService

logger = logging.getLogger(__name__)


class RoomScanAnalyzer:
    """Analyzes 360-degree room scans for suspicious items."""

    def __init__(
        self,
        groq_client,
        evidence_storage: EvidenceStorageService,
        db_session: Session
    ):
        self.groq_client = groq_client
        self.evidence_storage = evidence_storage
        self.db = db_session
        self.confidence_threshold: float = 0.70
        self.suspicious_items: List[str] = [
            "cell_phone", "smartphone", "monitor", "laptop", "book", "person", "tablet", "notes"
        ]

    async def analyze_scan(
        self,
        session_token: str,
        frames: List[bytes],
        scan_type: str
    ) -> dict:
        """
        Analyze all frames from 360-degree scan.
        Returns structured report with violations.
        """
        try:
            # Create room scan record
            room_scan = RoomScan(
                session_token=session_token,
                scan_type=scan_type,
                scan_status="processing",
                created_at=datetime.now(timezone.utc)
            )
            self.db.add(room_scan)
            self.db.flush()

            all_detections = []
            flagged_violations = []

            # Analyze each frame
            for idx, frame_data in enumerate(frames):
                detections = await self.detect_objects_in_frame(frame_data, idx)
                all_detections.extend(detections)

                # Check for violations
                violations = self.flag_violations(detections)
                if violations:
                    flagged_violations.extend(violations)

                # Persist every frame so HR can review clean as well as flagged scans.
                storage_key = await self.evidence_storage.upload_evidence(
                    session_token=session_token,
                    evidence_type="photo",
                    file_data=frame_data,
                    mime_type="image/jpeg",
                    metadata={"room_scan_id": room_scan.id, "frame_index": idx}
                )

                if storage_key:
                    evidence_file = self.db.query(EvidenceFile).filter(
                        EvidenceFile.s3_key == storage_key
                    ).first()

                    if evidence_file:
                        scan_frame = RoomScanFrame(
                            room_scan_id=room_scan.id,
                            evidence_file_id=evidence_file.id,
                            frame_index=idx,
                            has_violation=bool(violations)
                        )
                        self.db.add(scan_frame)

            # Generate report
            report = self.generate_scan_report(
                session_token,
                all_detections,
                flagged_violations
            )

            # Update room scan with results
            room_scan.scan_status = "completed"
            room_scan.verdict = report["verdict"]
            room_scan.suspicious_items_json = json.dumps(report["suspicious_items"])
            room_scan.completed_at = datetime.now(timezone.utc)

            # Update risk score
            if report["verdict"] in ["fail", "warning"]:
                self.update_risk_score(session_token, flagged_violations)

            self.db.commit()

            logger.info(f"Room scan analysis complete for {session_token}: {report['verdict']}")
            return report

        except Exception as e:
            logger.error(f"Room scan analysis failed: {e}")
            self.db.rollback()
            return {
                "verdict": "error",
                "suspicious_items": [],
                "violations": [],
                "error": str(e)
            }

    async def detect_objects_in_frame(
        self,
        frame_data: bytes,
        frame_index: int
    ) -> List[dict]:
        """
        Detect objects in a single frame using Groq API.
        Returns list of detections with confidence scores.
        """
        try:
            frame_b64 = base64.b64encode(frame_data).decode('utf-8')

            prompt = f"""Analyze this room scan frame and detect any suspicious items:
- Cell phones or smartphones
- Additional monitors or screens
- Laptops or tablets
- Books or notebooks
- Papers with notes
- Additional people in the room

Respond in JSON format:
{{
  "objects": [
    {{
      "item": "object name",
      "confidence": 0.0-1.0,
      "location": "where in frame"
    }}
  ],
  "people_count": number
}}"""

            if self.groq_client:
                response = self.groq_client.chat.completions.create(
                    model="llama-3.2-90b-vision-preview",
                    messages=[{"role": "user", "content": prompt}],
                    temperature=0.1,
                    max_tokens=512
                )
                content = response.choices[0].message.content
                analysis = json.loads(content)

                detections = []
                for obj in analysis.get("objects", []):
                    detections.append({
                        "frame_index": frame_index,
                        "item": obj.get("item", "unknown"),
                        "confidence": obj.get("confidence", 0.0),
                        "location": obj.get("location", ""),
                        "people_count": analysis.get("people_count", 0)
                    })

                return detections

        except Exception as e:
            logger.error(f"Object detection failed for frame {frame_index}: {e}")

        return []

    def flag_violations(
        self,
        detections: List[dict]
    ) -> List[dict]:
        """Flag detections that exceed confidence threshold."""
        violations = []

        for detection in detections:
            confidence = detection.get("confidence", 0.0)
            item = detection.get("item", "").lower()
            people_count = detection.get("people_count", 0)

            # Flag high-confidence suspicious items
            if confidence >= self.confidence_threshold:
                for suspicious_item in self.suspicious_items:
                    if suspicious_item in item:
                        violations.append({
                            "item": item,
                            "confidence": confidence,
                            "frame_index": detection.get("frame_index"),
                            "severity": "critical" if confidence >= 0.9 else "high"
                        })
                        break

            # Flag multiple people
            if people_count > 1:
                violations.append({
                    "item": "multiple_people",
                    "confidence": 1.0,
                    "frame_index": detection.get("frame_index"),
                    "severity": "critical",
                    "people_count": people_count
                })

        return violations

    def generate_scan_report(
        self,
        session_token: str,
        all_detections: List[dict],
        flagged_violations: List[dict]
    ) -> dict:
        """Generate structured report with verdict."""
        # Count violations by type
        violation_counts = {}
        for violation in flagged_violations:
            item = violation["item"]
            violation_counts[item] = violation_counts.get(item, 0) + 1

        # Determine verdict
        critical_violations = [v for v in flagged_violations if v.get("severity") == "critical"]

        if critical_violations:
            verdict = "fail"
        elif len(flagged_violations) >= 3:
            verdict = "warning"
        elif len(flagged_violations) > 0:
            verdict = "warning"
        else:
            verdict = "pass"

        return {
            "session_token": session_token,
            "verdict": verdict,
            "total_frames": len(set(d.get("frame_index") for d in all_detections)),
            "total_detections": len(all_detections),
            "total_violations": len(flagged_violations),
            "critical_violations": len(critical_violations),
            "suspicious_items": violation_counts,
            "violations": flagged_violations
        }

    def update_risk_score(
        self,
        session_token: str,
        violations: List[dict]
    ) -> None:
        """Update session risk score based on violations."""
        try:
            # Import here to avoid circular dependency
            from core.models import TestSession, CodingSession, LiveSession

            # Calculate risk penalty
            risk_penalty = 0
            for violation in violations:
                if violation.get("severity") == "critical":
                    risk_penalty += 10
                elif violation.get("severity") == "high":
                    risk_penalty += 5
                else:
                    risk_penalty += 2

            # Update session risk score
            for session_model in [TestSession, CodingSession, LiveSession]:
                session = self.db.query(session_model).filter(
                    session_model.token == session_token
                ).first()

                if session:
                    current_risk = getattr(session, "risk_score", 0) or 0
                    session.risk_score = current_risk + risk_penalty

                    # Update risk level
                    if session.risk_score >= 12:
                        session.proctoring_risk = "severe"
                    elif session.risk_score >= 9:
                        session.proctoring_risk = "critical"
                    elif session.risk_score >= 6:
                        session.proctoring_risk = "high"
                    elif session.risk_score >= 3:
                        session.proctoring_risk = "medium"

                    self.db.commit()
                    logger.info(f"Updated risk score for {session_token}: +{risk_penalty}")
                    break

        except Exception as e:
            logger.error(f"Failed to update risk score: {e}")
            self.db.rollback()
