"""
Idempotent HR seed for AWS-only environments.

Creates or updates:
  rajkumar@hiresy.com / 123
"""
from __future__ import annotations

from core.auth import hash_password
from core.database import SessionLocal
from core.models import User


EMAIL = "rajkumar@hiresy.com"
PASSWORD = "123"
NAME = "Rajkumar"


def seed_user() -> None:
    db = SessionLocal()
    try:
        user = db.query(User).filter(User.email == EMAIL).first()
        if user:
            user.name = NAME
            user.password = hash_password(PASSWORD)
            db.commit()
            print(f"Updated existing user: {EMAIL}")
        else:
            user = User(name=NAME, email=EMAIL, password=hash_password(PASSWORD))
            db.add(user)
            db.commit()
            print(f"Created user: {EMAIL}")
    finally:
        db.close()


if __name__ == "__main__":
    seed_user()
