"""
Runtime schema helpers for local/dev databases.

The project is still migrating from older per-service schemas into the shared
`core.models` definitions, so services call `ensure_runtime_schema()` on
startup to create missing tables and backfill newly-added columns.
"""
from __future__ import annotations

from sqlalchemy import inspect, text

from core.database import engine
from core.models import Base


_COLUMN_MIGRATIONS: dict[str, list[tuple[str, str]]] = {
    "applications": [
        ("status", "ALTER TABLE applications ADD COLUMN status VARCHAR DEFAULT 'pending'"),
    ],
    "verification_cases": [
        ("typed_city", "ALTER TABLE verification_cases ADD COLUMN typed_city VARCHAR"),
        ("typed_state", "ALTER TABLE verification_cases ADD COLUMN typed_state VARCHAR"),
        ("typed_pincode", "ALTER TABLE verification_cases ADD COLUMN typed_pincode VARCHAR"),
    ],
    "offer_workflows": [
        ("employment_type", "ALTER TABLE offer_workflows ADD COLUMN employment_type VARCHAR DEFAULT ''"),
        ("offered_compensation", "ALTER TABLE offer_workflows ADD COLUMN offered_compensation TEXT DEFAULT ''"),
        ("contract_duration_or_notes", "ALTER TABLE offer_workflows ADD COLUMN contract_duration_or_notes TEXT DEFAULT ''"),
        ("offer_valid_until", "ALTER TABLE offer_workflows ADD COLUMN offer_valid_until VARCHAR DEFAULT ''"),
    ],
    "live_hr_sessions": [
        ("interview_type", "ALTER TABLE live_hr_sessions ADD COLUMN interview_type VARCHAR DEFAULT 'copilot'"),
        ("hr_email", "ALTER TABLE live_hr_sessions ADD COLUMN hr_email VARCHAR DEFAULT ''"),
        ("ai_score_json", "ALTER TABLE live_hr_sessions ADD COLUMN ai_score_json TEXT DEFAULT '{}'"),
        ("ai_reason", "ALTER TABLE live_hr_sessions ADD COLUMN ai_reason TEXT DEFAULT ''"),
        ("ai_flags_json", "ALTER TABLE live_hr_sessions ADD COLUMN ai_flags_json TEXT DEFAULT '[]'"),
        ("manual_score_json", "ALTER TABLE live_hr_sessions ADD COLUMN manual_score_json TEXT DEFAULT '{}'"),
        ("manual_reason", "ALTER TABLE live_hr_sessions ADD COLUMN manual_reason TEXT DEFAULT ''"),
        ("final_summary", "ALTER TABLE live_hr_sessions ADD COLUMN final_summary TEXT DEFAULT ''"),
        ("reference_face_b64", "ALTER TABLE live_hr_sessions ADD COLUMN reference_face_b64 TEXT"),
    ],
    "shortlist_tests": [
        ("assessment_kind", "ALTER TABLE shortlist_tests ADD COLUMN assessment_kind VARCHAR DEFAULT 'mcq'"),
        ("proctoring_risk", "ALTER TABLE shortlist_tests ADD COLUMN proctoring_risk VARCHAR"),
        ("risk_score", "ALTER TABLE shortlist_tests ADD COLUMN risk_score FLOAT"),
        ("block_reason", "ALTER TABLE shortlist_tests ADD COLUMN block_reason VARCHAR"),
        ("face_continuity_score", "ALTER TABLE shortlist_tests ADD COLUMN face_continuity_score FLOAT"),
        ("verification_face_b64", "ALTER TABLE shortlist_tests ADD COLUMN verification_face_b64 TEXT"),
        ("proctoring_json", "ALTER TABLE shortlist_tests ADD COLUMN proctoring_json TEXT"),
    ],
    "coding_rounds": [
        ("round_type", "ALTER TABLE coding_rounds ADD COLUMN round_type VARCHAR DEFAULT 'coding'"),
        ("questions_json", "ALTER TABLE coding_rounds ADD COLUMN questions_json TEXT"),
        ("resume_text", "ALTER TABLE coding_rounds ADD COLUMN resume_text TEXT"),
        ("risk_score", "ALTER TABLE coding_rounds ADD COLUMN risk_score FLOAT"),
        ("block_reason", "ALTER TABLE coding_rounds ADD COLUMN block_reason VARCHAR"),
        ("face_continuity_score", "ALTER TABLE coding_rounds ADD COLUMN face_continuity_score FLOAT"),
        ("verification_face_b64", "ALTER TABLE coding_rounds ADD COLUMN verification_face_b64 TEXT"),
        ("proctoring_risk", "ALTER TABLE coding_rounds ADD COLUMN proctoring_risk VARCHAR"),
        ("authenticity_score", "ALTER TABLE coding_rounds ADD COLUMN authenticity_score INTEGER"),
        ("proctoring_json", "ALTER TABLE coding_rounds ADD COLUMN proctoring_json TEXT"),
        ("problems_json", "ALTER TABLE coding_rounds ADD COLUMN problems_json TEXT"),
    ],
}


def ensure_runtime_schema() -> None:
    """
    Create missing tables and add missing columns.
    Handles existing tables gracefully to avoid conflicts.
    """
    try:
        # Create tables only if they don't exist (checkfirst is True by default)
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        # If tables already exist, that's fine - continue with column migrations
        print(f"Note: Some tables may already exist: {e}")

    inspector = inspect(engine)
    for table_name, migrations in _COLUMN_MIGRATIONS.items():
        if not inspector.has_table(table_name):
            continue
        existing_columns = {column["name"] for column in inspector.get_columns(table_name)}
        with engine.connect() as conn:
            for column_name, sql in migrations:
                if column_name in existing_columns:
                    continue
                try:
                    conn.execute(text(sql))
                    conn.commit()
                except Exception as e:
                    # Column might already exist from a previous migration
                    print(f"Warning: Could not add column {column_name} to {table_name}: {e}")
                    conn.rollback()
