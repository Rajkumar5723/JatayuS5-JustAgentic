from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.sql import func
from database import Base


class User(Base):
    __tablename__ = "users"

    id       = Column(Integer, primary_key=True, index=True)
    name     = Column(String, nullable=False)
    email    = Column(String, unique=True, index=True)
    password = Column(String)


class Job(Base):
    __tablename__ = "jobs"

    id                 = Column(Integer, primary_key=True, index=True)
    posted_by          = Column(String, index=True)
    job_name           = Column(String, nullable=False)
    description        = Column(Text, nullable=False)
    salary_start       = Column(String)
    salary_end         = Column(String)
    show_salary        = Column(String, default="false")
    work_style         = Column(String)
    job_type           = Column(String)
    skills             = Column(String)
    exp_min            = Column(String)
    exp_max            = Column(String)
    department         = Column(String)
    openings           = Column(Integer)
    deadline           = Column(String)
    application_fields = Column(Text)
    difficulty         = Column(String)
    rounds             = Column(Text)
    platforms          = Column(String)
    created_at         = Column(DateTime(timezone=True), server_default=func.now())


class Application(Base):
    __tablename__ = "applications"

    id              = Column(Integer, primary_key=True, index=True)
    job_id          = Column(Integer, nullable=False)
    submitted_at    = Column(DateTime, default=datetime.utcnow)

    # Personal
    full_name       = Column(String, nullable=True)
    email           = Column(String, nullable=True)
    phone           = Column(String, nullable=True)
    alt_phone       = Column(String, nullable=True)
    location        = Column(String, nullable=True)

    # Resume / links
    resume_url      = Column(String, nullable=True)
    linkedin_url    = Column(String, nullable=True)
    github_url      = Column(String, nullable=True)
    leetcode_url    = Column(String, nullable=True)
    portfolio_url   = Column(String, nullable=True)

    # Education
    degree_type     = Column(String, nullable=True)
    field_of_study  = Column(String, nullable=True)
    institution     = Column(String, nullable=True)

    # Experience
    years_exp       = Column(String, nullable=True)
    current_title   = Column(String, nullable=True)
    company_name    = Column(String, nullable=True)
    current_lpa     = Column(String, nullable=True)
    notice_period   = Column(String, nullable=True)

    # Skills
    technical_skills = Column(String, nullable=True)
    soft_skills      = Column(String, nullable=True)

    # Extra
    cover_letter    = Column(String, nullable=True)

    # Status
    status          = Column(String, default="pending")  # pending | selected | rejected

    # Stage 0 — AI evaluation
    eval_score          = Column(String, nullable=True)
    eval_recommendation = Column(String, nullable=True)
    eval_summary        = Column(String, nullable=True)
    eval_data           = Column(Text,   nullable=True)
    status          = Column(String, default='pending')  

    # Stage 0 — AI evaluation
    eval_score          = Column(String, nullable=True)
    eval_recommendation = Column(String, nullable=True)
    eval_summary        = Column(String, nullable=True)
    eval_data           = Column(String, nullable=True)


