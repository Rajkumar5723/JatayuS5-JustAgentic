"""
services/main_api/routers/auth.py
==================================
POST /register  — create HR account
POST /login     — verify credentials
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import User
from core.auth import hash_password, verify_password

router = APIRouter(tags=["auth"])


class UserCreate(BaseModel):
    name: str
    email: str
    password: str


class UserLogin(BaseModel):
    email: str
    password: str


@router.post("/register", summary="Register a new HR account")
def register(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "Email already registered")
    db.add(User(name=body.name, email=body.email, password=hash_password(body.password)))
    db.commit()
    return {"message": "Registered successfully"}


@router.post("/login", summary="Login and return user info")
def login(body: UserLogin, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.password):
        raise HTTPException(400, "Invalid credentials")
    return {"message": "Login successful", "email": user.email, "name": user.name}


@router.get("/user-profile", summary="Get HR user name/email from database (for dashboard profile)")
def get_user_profile(email: str = Query(..., description="HR account email"), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == email).first()
    if not user:
        raise HTTPException(404, "User not found")
    return {"email": user.email, "name": user.name}
