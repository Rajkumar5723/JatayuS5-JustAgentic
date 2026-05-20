"""
migrate_db.py
==============
Manually adds missing columns to the PostgreSQL database.
Run this if SQLAlchemy create_all() doesn't update existing tables.
"""
from __future__ import annotations
import sys, os

# Ensure Backend/ is on the path
_backend = os.path.dirname(os.path.abspath(__file__))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

from sqlalchemy import text, create_engine
from core.config import settings

def migrate():
    engine = create_engine(settings.db_url)
    
    # List of SQL commands to add columns if they don't exist
    commands = [
        # Jobs table
        "ALTER TABLE jobs ADD COLUMN IF NOT EXISTS location TEXT;",
        
        # Live Sessions table
        "ALTER TABLE live_hr_sessions ADD COLUMN IF NOT EXISTS interview_type VARCHAR DEFAULT 'copilot';",
        
        # Coding Rounds table (Proctoring + Multi-round)
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS round_type VARCHAR DEFAULT 'coding';",
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS questions_json TEXT;",
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS resume_text TEXT;",
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS proctoring_risk VARCHAR;",
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS authenticity_score INTEGER;",
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS proctoring_json TEXT;",
        "ALTER TABLE coding_rounds ADD COLUMN IF NOT EXISTS problems_json TEXT;"
    ]
    
    with engine.connect() as conn:
        print(f"Connecting to {settings.db_url.split('@')[-1]}...")
        for cmd in commands:
            try:
                conn.execute(text(cmd))
                conn.commit()
                print(f"Executed: {cmd.strip()}")
            except Exception as e:
                print(f"Error executing {cmd.strip()}: {e}")
        print("Migration complete!")

if __name__ == "__main__":
    migrate()
