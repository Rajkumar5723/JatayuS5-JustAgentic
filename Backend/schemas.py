from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Auth ──────────────────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str

class UserLogin(BaseModel):
    email: EmailStr
    password: str


# ── Job ──────────────────────────────────────────────
class JobCreate(BaseModel):
    posted_by: EmailStr
    job_name: str
    description: str
    salary_start: Optional[str] = ""
    salary_end: Optional[str] = ""
    show_salary: Optional[str] = "false"
    work_style: Optional[str] = ""
    job_type: str
    skills: Optional[str] = ""
    exp_min: Optional[str] = ""
    exp_max: Optional[str] = ""
    department: str
    openings: int
    deadline: Optional[str] = ""
    application_fields: Optional[str] = ""
    difficulty: Optional[str] = "Easy"
    rounds: Optional[str] = ""
    platforms: Optional[str] = ""


class JobResponse(JobCreate):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True