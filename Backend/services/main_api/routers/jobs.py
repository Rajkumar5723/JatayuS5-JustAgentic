"""
services/main_api/routers/jobs.py
==================================
Full CRUD for Job postings + LinkedIn posting.
"""
from __future__ import annotations
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from core.database import get_db
from core.models import Job, User, Application
from core.interview_rounds import validate_rounds_config

router = APIRouter(tags=["jobs"])


# ── Pydantic schemas ──────────────────────────────────────────
class JobCreate(BaseModel):
    posted_by:          str
    job_name:           str
    description:        str
    salary_start:       Optional[str] = None
    salary_end:         Optional[str] = None
    show_salary:        Optional[str] = "false"
    work_style:         Optional[str] = None
    location:           Optional[str] = None
    job_type:           Optional[str] = None
    skills:             Optional[str] = None
    exp_min:            Optional[str] = None
    exp_max:            Optional[str] = None
    department:         Optional[str] = None
    openings:           Optional[int] = None
    deadline:           Optional[str] = None
    application_fields: Optional[str] = None
    difficulty:         Optional[str] = None
    rounds:             Optional[str] = None
    platforms:          Optional[str] = None


class JobResponse(BaseModel):
    id:                 int
    posted_by:          str
    job_name:           str
    description:        str
    salary_start:       Optional[str] = None
    salary_end:         Optional[str] = None
    show_salary:        Optional[str] = None
    work_style:         Optional[str] = None
    location:           Optional[str] = None
    job_type:           Optional[str] = None
    skills:             Optional[str] = None
    exp_min:            Optional[str] = None
    exp_max:            Optional[str] = None
    department:         Optional[str] = None
    openings:           Optional[int] = None
    deadline:           Optional[str] = None
    application_fields: Optional[str] = None
    difficulty:         Optional[str] = None
    rounds:             Optional[str] = None
    platforms:          Optional[str] = None

    class Config:
        from_attributes = True


# ── Endpoints ─────────────────────────────────────────────────
@router.post("/jobs", response_model=JobResponse, summary="Create a job posting")
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.email == job.posted_by).first():
        raise HTTPException(404, "HR user not found")
    if job.rounds:
        err = validate_rounds_config(job.rounds)
        if err:
            raise HTTPException(400, err)
    new_job = Job(**job.model_dump())
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@router.get("/jobs", response_model=List[JobResponse], summary="List all jobs")
def get_all_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@router.get("/jobs/my/{email}", response_model=List[JobResponse], summary="Jobs posted by an HR user")
def get_my_jobs(email: str, db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.posted_by == email).order_by(Job.created_at.desc()).all()


@router.get("/jobs/{job_id}", summary="Get a single job")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


@router.delete("/jobs/{job_id}", summary="Delete a job and all its applications")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    db.query(Application).filter(Application.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    return {"message": f"Job {job_id} and its applications deleted"}


@router.post("/jobs/{job_id}/post-linkedin", summary="Post a job to LinkedIn")
def post_to_linkedin(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    # Import here to avoid circular dependencies
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
    from linkedin_poster import generate_and_post  # type: ignore
    details = {
        "posted_by":   job.posted_by,
        "title":       job.job_name,
        "skills":      job.skills or "",
        "location":    (job.location or "").strip() or (job.work_style or ""),
        "salary":      f"Rs.{job.salary_start} - Rs.{job.salary_end}" if job.salary_start else "",
        "description": job.description,
        "job_type":    job.job_type,
        "department":  job.department,
        "openings":    job.openings,
        "deadline":    job.deadline or "",
    }
    return generate_and_post(str(job_id), details)
