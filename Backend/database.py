"""
Legacy compatibility shim.

Active services should import from `core.database`, but older scripts may still
import `Backend.database`. Re-export the shared engine/session/base so the repo
uses the same AWS-aware configuration everywhere.
"""
from core.database import Base, SessionLocal, engine, get_db

__all__ = ["Base", "SessionLocal", "engine", "get_db"]
