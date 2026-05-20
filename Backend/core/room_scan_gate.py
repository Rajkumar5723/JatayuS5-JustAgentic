"""
Helpers for enforcing the initial room scan requirement before test start.
"""
from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.orm import Session

from core.models import RoomScan

ACCEPTED_ROOM_SCAN_VERDICTS = {"pass", "warning"}


def get_latest_room_scan(
    db: Session,
    session_token: str,
    scan_type: str = "initial",
) -> RoomScan | None:
    query = db.query(RoomScan).filter(RoomScan.session_token == session_token)
    if scan_type:
        query = query.filter(RoomScan.scan_type == scan_type)
    return query.order_by(RoomScan.created_at.desc(), RoomScan.id.desc()).first()


def has_completed_initial_room_scan(db: Session, session_token: str) -> bool:
    scan = get_latest_room_scan(db, session_token, "initial")
    if not scan:
        return False
    if scan.scan_status != "completed":
        return False
    return scan.verdict in ACCEPTED_ROOM_SCAN_VERDICTS


def ensure_initial_room_scan_completed(db: Session, session_token: str) -> RoomScan:
    scan = get_latest_room_scan(db, session_token, "initial")
    if not scan:
        raise HTTPException(400, "Complete the room scan before starting this test.")

    if scan.scan_status != "completed":
        raise HTTPException(400, "Room scan is still processing. Please wait a moment and try again.")

    if scan.verdict not in ACCEPTED_ROOM_SCAN_VERDICTS:
        if scan.verdict == "fail":
            raise HTTPException(400, "Room scan failed. Remove suspicious items and scan the room again.")
        raise HTTPException(400, "A valid room scan is required before this test can begin.")

    return scan
