from fastapi import FastAPI, Depends, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from typing import List
import sqlite3, os, requests, urllib.parse

from database import SessionLocal, engine
from models import Base, User, Job
from schemas import UserCreate, UserLogin, JobCreate, JobResponse
from auth import hash_password, verify_password
from linkedin_poster import generate_and_post

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

Base.metadata.create_all(bind=engine)
# LLC
DB_PATH          = os.path.join(os.path.dirname(os.path.abspath(__file__)), "linkedin_automation.db")
LI_CLIENT_ID     = os.getenv("LI_CLIENT_ID", "")
LI_CLIENT_SECRET = os.getenv("LI_CLIENT_SECRET", "")
LI_REDIRECT_URI  = os.getenv("LI_REDIRECT_URI", "http://localhost:8000/linkedin/callback")
LI_SCOPE         = os.getenv("LI_SCOPE", "openid profile w_member_social")


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("PRAGMA table_info(linkedin_accounts)")
    cols = [r[1] for r in cur.fetchall()]
    if cols and "person_urn" not in cols:
        conn.execute("DROP TABLE linkedin_accounts")
    conn.execute("""
        CREATE TABLE IF NOT EXISTS linkedin_accounts (
            hr_email     TEXT PRIMARY KEY,
            person_urn   TEXT,
            access_token TEXT NOT NULL,
            expires_at   TEXT
        )
    """)
    conn.commit()
    conn.close()

init_db()

import json as _json

EVAL_SERVICE_URL = "http://127.0.0.1:8001/eval/evaluate"

def trigger_evaluation(app_id: int, payload: dict):
    """Background task: calls eval microservice after application submission."""
    try:
        from models import Application, Job
        from database import SessionLocal
        db2 = SessionLocal()

        app_entry = db2.query(Application).filter(Application.id == app_id).first()
        if not app_entry: return

        job = db2.query(Job).filter(Job.id == app_entry.job_id).first()
        job_description = f"{job.job_name}\n{job.description}\nSkills: {job.skills}" if job else ""

        eval_payload = {
            "application_id":  app_id,
            "resume_text":     f"""
Name: {app_entry.full_name}
Current Title: {app_entry.current_title}
Company: {app_entry.company_name}
Experience: {app_entry.years_exp} years
Education: {app_entry.degree_type} in {app_entry.field_of_study} from {app_entry.institution}
Technical Skills: {app_entry.technical_skills}
Soft Skills: {app_entry.soft_skills}
""",
            "job_description": job_description,
            "github_url":      app_entry.github_url or "",
            "linkedin_url":    app_entry.linkedin_url or "",
            "leetcode_url":    app_entry.leetcode_url or "",
        }

        res = requests.post(EVAL_SERVICE_URL, json=eval_payload, timeout=90)
        if res.ok:
            result = res.json()
            app_entry.eval_score          = result.get("final_score")
            app_entry.eval_recommendation = result.get("hiring_recommendation")
            app_entry.eval_summary        = result.get("summary")
            app_entry.eval_data           = _json.dumps(result)
            db2.commit()
            print(f"[Eval] App {app_id} scored: {result.get('final_score')} — {result.get('hiring_recommendation')}")
        else:
            print(f"[Eval] Service error for app {app_id}: {res.text[:200]}")

        db2.close()
    except Exception as e:
        print(f"[Eval] Failed for app {app_id}: {e}")


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── ROOT ───────────────────────────────────────────────
@app.get("/")
def root():
    return {"message": "Hiersy API running"}


# ── AUTH ───────────────────────────────────────────────
@app.post("/register")
def register(user: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == user.email).first():
        raise HTTPException(400, "Email already registered")
    db.add(User(name=user.name, email=user.email, password=hash_password(user.password)))
    db.commit()
    return {"message": "Registered successfully"}


@app.post("/login")
def login(user: UserLogin, db: Session = Depends(get_db)):
    db_user = db.query(User).filter(User.email == user.email).first()
    if not db_user or not verify_password(user.password, db_user.password):
        raise HTTPException(400, "Invalid credentials")
    return {"message": "Login successful", "email": db_user.email, "name": db_user.name}


# ── LINKEDIN OAUTH ─────────────────────────────────────
@app.get("/linkedin/connect")
def linkedin_connect(email: str):
    params = {
        "response_type": "code",
        "client_id":     LI_CLIENT_ID,
        "redirect_uri":  LI_REDIRECT_URI,
        "scope":         LI_SCOPE,
        "state":         email,
    }
    url = "https://www.linkedin.com/oauth/v2/authorization?" + urllib.parse.urlencode(params)
    return RedirectResponse(url)


@app.get("/linkedin/callback")
def linkedin_callback(code: str = None, state: str = None, error: str = None):
    if error or not code:
        print(f"[LinkedIn] OAuth error: {error}")
        return RedirectResponse("http://localhost:5173/hrdashboard/all?linkedin=error")

    hr_email = state
    print(f"[LinkedIn] Callback: hr_email={hr_email}")

    res = requests.post(
        "https://www.linkedin.com/oauth/v2/accessToken",
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  LI_REDIRECT_URI,
            "client_id":     LI_CLIENT_ID,
            "client_secret": LI_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"}
    )
    token_data   = res.json()
    print(f"[LinkedIn] Token response: {token_data}")
    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse("http://localhost:5173/hrdashboard/all?linkedin=error")

    # Get person URN via OpenID
    info = requests.get(
        "https://api.linkedin.com/v2/userinfo",
        headers={"Authorization": f"Bearer {access_token}"}
    )
    print(f"[LinkedIn] userinfo: {info.status_code} {info.text[:200]}")
    person_urn = ""
    if info.status_code == 200:
        sub        = info.json().get("sub", "")
        person_urn = f"urn:li:person:{sub}"

    print(f"[LinkedIn] Saving person_urn={person_urn}")
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        INSERT OR REPLACE INTO linkedin_accounts (hr_email, person_urn, access_token, expires_at)
        VALUES (?, ?, ?, datetime('now', '+60 days'))
    """, (hr_email, person_urn, access_token))
    conn.commit()
    conn.close()
    print("[LinkedIn] Saved!")

    return RedirectResponse("http://localhost:5173/hrdashboard/all?linkedin=connected")


@app.get("/linkedin/status/{email}")
def linkedin_status(email: str):
    conn = sqlite3.connect(DB_PATH)
    cur  = conn.cursor()
    cur.execute("SELECT person_urn FROM linkedin_accounts WHERE hr_email = ?", (email,))
    row  = cur.fetchone()
    conn.close()
    return {"connected": bool(row)}


@app.delete("/linkedin/disconnect/{email}")
def linkedin_disconnect(email: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("DELETE FROM linkedin_accounts WHERE hr_email = ?", (email,))
    conn.commit()
    conn.close()
    return {"message": "Disconnected"}


# ── JOBS ───────────────────────────────────────────────
@app.post("/jobs", response_model=JobResponse)
def create_job(job: JobCreate, db: Session = Depends(get_db)):
    if not db.query(User).filter(User.email == job.posted_by).first():
        raise HTTPException(404, "HR user not found")
    new_job = Job(**job.model_dump())
    db.add(new_job)
    db.commit()
    db.refresh(new_job)
    return new_job


@app.post("/jobs/{job_id}/post-linkedin")
def post_job_to_linkedin(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    job_details = {
        "posted_by":   job.posted_by,
        "title":       job.job_name,
        "skills":      job.skills or "",
        "location":    job.work_style or "",
        "salary":      f"Rs.{job.salary_start} - Rs.{job.salary_end}" if job.salary_start else "",
        "description": job.description,
        "job_type":    job.job_type,
        "department":  job.department,
        "openings":    job.openings,
        "deadline":    job.deadline or "",
    }
    return generate_and_post(str(job_id), job_details)


@app.get("/jobs", response_model=List[JobResponse])
def get_all_jobs(db: Session = Depends(get_db)):
    return db.query(Job).order_by(Job.created_at.desc()).all()


@app.get("/jobs/my/{email}", response_model=List[JobResponse])
def get_my_jobs(email: str, db: Session = Depends(get_db)):
    return db.query(Job).filter(Job.posted_by == email).order_by(Job.created_at.desc()).all()


@app.delete("/jobs/{job_id}")
def delete_job(job_id: int, db: Session = Depends(get_db)):
    from models import Application
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    db.query(Application).filter(Application.job_id == job_id).delete()
    db.delete(job)
    db.commit()
    return {"message": f"Job {job_id} and all its applications deleted"}


# ── PUBLIC: GET SINGLE JOB ─────────────────────────────
@app.get("/jobs/{job_id}")
def get_job(job_id: int, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == job_id).first()
    if not job:
        raise HTTPException(404, "Job not found")
    return job


# ── SUBMIT APPLICATION ─────────────────────────────────
@app.post("/applications")
def submit_application(payload: dict, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from models import Application
    import json

    valid_columns = {c.name for c in Application.__table__.columns}

    known_fields  = {k: v for k, v in payload.items() if k in valid_columns and k != "stage"}
    custom_fields = {k: v for k, v in payload.items() if k not in valid_columns and k != "stage"}

    app_entry = Application(**known_fields)
    app_entry.status = "pending"

   
    if hasattr(app_entry, "extra_fields") and custom_fields:
        app_entry.extra_fields = json.dumps(custom_fields)

    db.add(app_entry)
    db.commit()
    db.refresh(app_entry)

    background_tasks.add_task(trigger_evaluation, app_entry.id, payload)
    return {"message": "Application submitted!", "id": app_entry.id}


@app.get("/applications/job/{job_id}/count")
def get_application_count(job_id: int, db: Session = Depends(get_db)):
    from models import Application
    return {"count": db.query(Application).filter(Application.job_id == job_id).count()}


@app.get("/applications/{job_id}")
def get_applications(job_id: int, db: Session = Depends(get_db)):
    from models import Application
    return db.query(Application).filter(Application.job_id == job_id).all()


@app.get("/application/{app_id}")
def get_single_application(app_id: int, db: Session = Depends(get_db)):
    from models import Application, Job
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    data = {c.name: getattr(app_entry, c.name) for c in app_entry.__table__.columns}
    data["job_name"] = job.job_name if job else "Unknown Position"
    return data


@app.get("/applications/{app_id}/tests")
def get_application_tests(app_id: int, db: Session = Depends(get_db)):
    from models import TestSession, CodingSession, LiveSession
    
    tests = []
    
    # 1. Shortlist Tests
    shortlists = db.query(TestSession).filter(TestSession.application_id == app_id).all()
    for s in shortlists:
        tests.append({
            "type": "shortlist_test",
            "title": "Shortlisting Test",
            "status": s.status,
            "score_pct": s.score_pct,
            "passed": s.passed,
            "pass_score": s.pass_score,
            "created_at": s.created_at.isoformat() if s.created_at else None,
            "submitted_at": s.submitted_at.isoformat() if s.submitted_at else None,
            "proctoring_risk": s.proctoring_risk,
            "block_reason": s.block_reason,
            "proctoring_json": s.proctoring_json,
            "ai_reason": None,
            "ai_flags_json": "[]"
        })
        
    # 2. Coding Tests
    codings = db.query(CodingSession).filter(CodingSession.application_id == app_id).all()
    for c in codings:
        round_type_label = {
            "coding": "Coding Test",
            "oop": "OOP Design Test",
            "database": "Database Test",
            "api": "API Integration Test"
        }.get(c.round_type, "Technical Test")
        
        tests.append({
            "type": f"coding_test_{c.round_type}",
            "title": round_type_label,
            "status": c.status,
            "score_pct": c.score_pct,
            "passed": c.passed,
            "pass_score": c.pass_score,
            "created_at": c.created_at.isoformat() if c.created_at else None,
            "submitted_at": c.submitted_at.isoformat() if c.submitted_at else None,
            "proctoring_risk": c.proctoring_risk,
            "block_reason": c.block_reason,
            "proctoring_json": c.proctoring_json,
            "authenticity_score": c.authenticity_score,
            "ai_reason": None,
            "ai_flags_json": "[]"
        })
        
    # 3. Live HR Sessions
    lives = db.query(LiveSession).filter(LiveSession.application_id == app_id).all()
    for l in lives:
        tests.append({
            "type": "live_session",
            "title": "Live Interview" if l.interview_type == "hr_interview" else "AI Copilot Interview",
            "status": l.status,
            "score_pct": None,
            "passed": True if l.outcome == "pass" else (False if l.outcome == "fail" else None),
            "pass_score": None,
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "submitted_at": None,
            "proctoring_risk": None,
            "block_reason": None,
            "proctoring_json": "{}",
            "ai_reason": l.ai_reason or l.manual_reason or l.final_summary,
            "ai_flags_json": l.ai_flags_json
        })
        
    # Sort descending by created_at
    tests.sort(key=lambda x: x["created_at"] or "", reverse=True)
    return tests



# RESUME EXTRACTION
@app.post("/extract-resume")
async def extract_resume(request: Request):
    import base64, re, tempfile, os
    import pdfplumber

    body       = await request.json()
    pdf_base64 = body.get("pdf_base64")
    if not pdf_base64:
        raise HTTPException(400, "pdf_base64 required")

    pdf_bytes = base64.b64decode(pdf_base64)
    with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as f:
        f.write(pdf_bytes)
        tmp_path = f.name

    try:
        text = ""
        with pdfplumber.open(tmp_path) as pdf:
            for page in pdf.pages:
                text += (page.extract_text() or "") + "\n"
    finally:
        os.unlink(tmp_path)

    lines = [l.strip() for l in text.splitlines() if l.strip()]
    full_text = text

    # ── helpers ──────────────────────────────────────────────────
    def find_section(headers: list[str]) -> int:
        """Return line index of the first matching section header, or -1."""
        for i, line in enumerate(lines):
            for h in headers:
                if re.match(rf"^{re.escape(h)}\s*[:\-]?\s*$", line, re.IGNORECASE):
                    return i
                if re.match(rf"^{re.escape(h)}\b", line, re.IGNORECASE) and len(line) < 40:
                    return i
        return -1

    def get_section_lines(headers: list[str], max_lines: int = 20) -> list[str]:
        """Return lines under a section until the next section starts."""
        start = find_section(headers)
        if start < 0:
            return []
        section_headers = [
            "experience", "education", "skills", "projects", "certif",
            "awards", "publications", "languages", "interests", "summary",
            "objective", "profile", "work", "employment", "academic",
            "achievements", "extracurricular", "volunteer", "hobbies",
            "technical", "professional", "contact", "links", "portfolio"
        ]
        result = []
        for line in lines[start + 1: start + 1 + max_lines]:
            if any(re.match(rf"^{h}\b", line, re.IGNORECASE) and len(line) < 50
                   for h in section_headers):
                break
            result.append(line)
        return result

    # ── Name ─────────────────────────────────────────────────────
    # First non-empty line that isn't an email/phone/url
    full_name = ""
    for line in lines[:5]:
        if not re.search(r'[@/\\.]com|^\+?\d[\d\s\-]{8,}|http', line, re.IGNORECASE):
            if len(line.split()) >= 2 and len(line) < 60:
                full_name = line
                break
    if not full_name and lines:
        full_name = lines[0]

    # ── Email ─────────────────────────────────────────────────────
    em = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', full_text)
    email = em.group(0) if em else ""

    # ── Phone ─────────────────────────────────────────────────────
    ph = re.search(r'(\+?[\d][\d\s\-().]{9,14}\d)', full_text)
    phone = ph.group(1).strip() if ph else ""

    # ── URLs ──────────────────────────────────────────────────────
    def extract_url(pattern):
        m = re.search(pattern, full_text, re.IGNORECASE)
        if not m:
            return ""
        url = m.group(0).strip().rstrip(".,)|>")
        if not url.startswith("http"):
            url = "https://" + url
        return url

    linkedin  = extract_url(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+')
    github    = extract_url(r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+')
    leetcode  = extract_url(r'(?:https?://)?(?:www\.)?leetcode\.com/[\w\-]+')
    portfolio = extract_url(r'(?:https?://)?[\w\-]+\.(?:vercel\.app|netlify\.app|github\.io)[^\s,]*')

    # ── Location ──────────────────────────────────────────────────
    # Strategy 1: look for "City, State" or "City, Country" pattern in first 10 lines
    location = ""
    loc_patterns = [
        r'\b([A-Z][a-zA-Z\s]+,\s*(?:Tamil Nadu|Karnataka|Maharashtra|Delhi|Telangana|Kerala|Gujarat|Rajasthan|Punjab|UP|India|USA|UK|Canada|Australia|Germany|France|Singapore|Remote))\b',
        r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)?,\s*[A-Z][a-z]+(?: [A-Z][a-z]+)?)\b',
    ]
    # First scan header lines (first 8)
    header_text = "\n".join(lines[:8])
    for pat in loc_patterns:
        m = re.search(pat, header_text)
        if m:
            location = m.group(1).strip()
            break

    # Strategy 2: look for standalone city/state keywords in first 8 lines
    if not location:
        city_keywords = [
            "Chennai", "Bangalore", "Mumbai", "Delhi", "Hyderabad", "Pune",
            "Kolkata", "Ahmedabad", "Jaipur", "Surat", "Lucknow", "Kochi",
            "Coimbatore", "Madurai", "Pondicherry", "Puducherry",
            "New York", "San Francisco", "London", "Toronto", "Singapore",
            "Remote", "Bengaluru", "Noida", "Gurgaon", "Gurugram"
        ]
        for line in lines[:8]:
            for city in city_keywords:
                if city.lower() in line.lower():
                    location = line.strip()
                    break
            if location:
                break

    # Strategy 3: fallback regex on full text
    if not location:
        for pat in loc_patterns:
            m = re.search(pat, full_text)
            if m:
                location = m.group(1).strip()
                break

    # ── Skills ────────────────────────────────────────────────────
    technical_skills = ""
    soft_skills_val  = ""

    skill_section = get_section_lines(
        ["skills", "technical skills", "technologies", "tech stack",
         "core competencies", "competencies", "tools & technologies",
         "tools and technologies", "programming skills"],
        max_lines=30
    )

    if skill_section:
        raw_skills = []
        for line in skill_section:
            # Handle "Category: skill1, skill2, skill3" format
            colon_match = re.match(r'^[\w\s/&]+:\s*(.+)', line)
            if colon_match:
                raw_skills.append(colon_match.group(1))
            else:
                # Handle bullet points and plain lines
                cleaned = re.sub(r'^[\•\-\*\u2022\u25cf\u25aa►▸→·]\s*', '', line)
                if cleaned:
                    raw_skills.append(cleaned)

        # Join everything, split by common delimiters
        all_skills_str = ", ".join(raw_skills)
        skill_tokens = re.split(r'[,|;•\n]+', all_skills_str)
        skill_tokens = [s.strip() for s in skill_tokens if s.strip() and len(s.strip()) > 1]

        # Soft skill keywords to separate out
        soft_kw = ["communication", "teamwork", "leadership", "problem solving",
                   "time management", "adaptability", "critical thinking",
                   "collaboration", "interpersonal", "presentation", "creativity"]

        tech_list, soft_list = [], []
        for skill in skill_tokens:
            if any(kw in skill.lower() for kw in soft_kw):
                soft_list.append(skill)
            else:
                tech_list.append(skill)

        technical_skills = ", ".join(tech_list)
        soft_skills_val  = ", ".join(soft_list)

    # If no dedicated skill section found, try scanning for known tech keywords
    if not technical_skills:
        known_tech = [
            "Python", "Java", "JavaScript", "TypeScript", "C\\+\\+", "C#", "C ",
            "Ruby", "Go", "Rust", "Kotlin", "Swift", "PHP", "R ", "Dart", "Scala",
            "HTML", "CSS", "SASS", "React", "Angular", "Vue", "Next\\.js", "Node\\.js",
            "Express", "Django", "Flask", "Spring", "FastAPI", "Laravel",
            "MySQL", "PostgreSQL", "MongoDB", "SQLite", "Firebase", "Redis",
            "Supabase", "AWS", "Azure", "GCP", "Docker", "Kubernetes",
            "TailwindCSS", "Tailwind", "Bootstrap", "Figma", "Tableau",
            "Excel", "Power BI", "Git", "Linux", "Jotai", "UiPath",
        ]
        found = []
        for tech in known_tech:
            if re.search(rf'\b{tech}\b', full_text, re.IGNORECASE):
                found.append(tech.replace("\\.", ".").replace("\\+", "+"))
        technical_skills = ", ".join(found)

    # ── Education ─────────────────────────────────────────────────
    degree_type    = ""
    field_of_study = ""
    institution    = ""

    edu_lines = get_section_lines(
        ["education", "academic background", "academic qualifications", "qualifications"],
        max_lines=15
    )

    degree_patterns = [
        r'\b(B\.?Tech|B\.?E\.?|B\.?Sc\.?|B\.?C\.?A|M\.?Tech|M\.?Sc\.?|M\.?B\.?A|M\.?C\.?A|Ph\.?D|B\.?Com|Diploma|Bachelor|Master|Associate)\b',
    ]
    if edu_lines:
        for line in edu_lines:
            for pat in degree_patterns:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    degree_type = m.group(1)
                    # Try to extract field after "in" or "of"
                    in_m = re.search(r'(?:in|of)\s+([A-Za-z\s&]+?)(?:\s*[-,|]\s*|\s*\d{4}|$)', line, re.IGNORECASE)
                    if in_m:
                        field_of_study = in_m.group(1).strip()
                    break
            if degree_type:
                # Institution is usually nearby — look for college/university keywords
                for edu_line in edu_lines:
                    if any(kw in edu_line.lower() for kw in
                           ["university", "college", "institute", "institution", "school", "iit", "nit", "bits"]):
                        institution = edu_line.strip()
                        break
                break

    # ── Experience ────────────────────────────────────────────────
    years_exp     = ""
    current_title = ""
    company_name  = ""

    # Years of experience — scan full text
    exp_patterns = [
        r'(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)[\s\w]{0,20}(?:of\s+)?(?:experience|exp)',
        r'(?:experience|exp)[^\d]{0,10}(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)',
    ]
    for pat in exp_patterns:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            years_exp = m.group(1)
            break

    exp_lines = get_section_lines(
        ["experience", "work experience", "professional experience",
         "employment history", "internship", "internships", "work history"],
        max_lines=20
    )

    if exp_lines:
        # Title patterns: "Software Engineer at Google" / "Software Engineer, Google"
        title_patterns = [
            r'^([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Designer|Manager|Analyst|Intern|Lead|Architect|Consultant|Scientist|Specialist))',
            r'^([\w\s]+(?:Intern|Developer|Engineer|Designer|Analyst|Manager|Lead))',
        ]
        for line in exp_lines:
            for pat in title_patterns:
                m = re.match(pat, line)
                if m:
                    current_title = m.group(1).strip()
                    # Try to get company from same line
                    at_m = re.search(r'(?:at|@|,|\|)\s*([A-Z][a-zA-Z\s]+?)(?:\s*[-|,]|\s*\d{4}|$)', line)
                    if at_m:
                        company_name = at_m.group(1).strip()
                    break
            if current_title:
                # If no company yet, check next lines
                if not company_name:
                    for next_line in exp_lines[exp_lines.index(line)+1:exp_lines.index(line)+3]:
                        if re.match(r'^[A-Z][a-zA-Z\s]+$', next_line) and len(next_line) < 50:
                            company_name = next_line.strip()
                            break
                break

    return {
        "full_name":        full_name,
        "email":            email,
        "phone":            phone,
        "location":         location,
        "linkedin_url":     linkedin,
        "github_url":       github,
        "leetcode_url":     leetcode,
        "portfolio_url":    portfolio,
        "degree_type":      degree_type,
        "field_of_study":   field_of_study,
        "institution":      institution,
        "years_exp":        years_exp,
        "current_title":    current_title,
        "company_name":     company_name,
        "current_lpa":      "",
        "notice_period":    "",
        "technical_skills": technical_skills,
        "soft_skills":      soft_skills_val,
    }


# ── RETRY EVALUATION ──────────────────────────────────
@app.post("/applications/{app_id}/retry-eval")
def retry_evaluation(app_id: int, background_tasks: BackgroundTasks, db: Session = Depends(get_db)):
    from models import Application
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    payload = {
        "github_url":      app_entry.github_url or "",
        "linkedin_url":    app_entry.linkedin_url or "",
        "leetcode_url":    app_entry.leetcode_url or "",
        "technical_skills": app_entry.technical_skills or "",
        "soft_skills":     app_entry.soft_skills or "",
    }
    background_tasks.add_task(trigger_evaluation, app_id, payload)
    return {"message": "Evaluation retrying..."}


# ── LINKEDIN PROFILE SCRAPE ────────────────────────────
@app.get("/linkedin/profile")
def get_linkedin_profile(url: str):
    from linkedin_scraper import scrape_linkedin  # type: ignore
    try:
        data = scrape_linkedin(url)
        return {"success": bool(data.get("name")), "data": data}
    except Exception as e:
        return {"success": False, "data": {}, "error": str(e)}


@app.patch("/applications/{app_id}/status")
def update_application_status(app_id: int, payload: dict, db: Session = Depends(get_db)):
    from models import Application, Job
    from core.email_utils import send_api_status_update_email
    from core.interview_rounds import generate_next_round_link
    import logging
    
    logger = logging.getLogger(__name__)
    
    app_entry = db.query(Application).filter(Application.id == app_id).first()
    if not app_entry:
        raise HTTPException(404, "Application not found")
    
    old_status = app_entry.status
    new_status = payload.get("status")
    app_entry.status = new_status
    db.commit()
    
    logger.info("Status update for app %s: %s → %s", app_id, old_status, new_status)
    
    # Get job information
    job = db.query(Job).filter(Job.id == app_entry.job_id).first()
    job_title = job.job_name if job else ""
    job_skills = job.skills if job else ""
    hr_email = job.posted_by if job else ""
    
    # Generate next round link using dynamic interview configuration
    next_round_url = None
    if new_status and old_status != new_status:
        next_round_url = generate_next_round_link(
            application_id=app_id,
            job_id=app_entry.job_id,  # Added job_id
            application_status=new_status,
            candidate_name=app_entry.full_name,
            candidate_email=app_entry.email,
            job_title=job_title,
            job_skills=job_skills,
            hr_email=hr_email,
            rounds_config=job.rounds if job else None,
        )
    
    logger.info("Sending status update email for app %s with url: %s", app_id, next_round_url)
    
    # Send email on meaningful status transitions
    try:
        if new_status and old_status != new_status:
            send_api_status_update_email(
                candidate_email=app_entry.email,
                candidate_name=app_entry.full_name,
                job_title=job_title,
                old_status=old_status,
                new_status=new_status,
                application_id=app_id,
                next_round_url=next_round_url,
            )
    except Exception as exc:
        logger.warning("Failed to send status update email: %s", exc)
    
    return {"message": "Status updated", "status": app_entry.status}
