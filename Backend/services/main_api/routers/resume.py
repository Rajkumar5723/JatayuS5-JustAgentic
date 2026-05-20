"""
services/main_api/routers/resume.py
=====================================
POST /extract-resume — parse a base64-encoded PDF and return structured fields.
"""
from __future__ import annotations
import base64
import os
import re
import tempfile

from fastapi import APIRouter, HTTPException, Request

router = APIRouter(tags=["resume"])


@router.post("/extract-resume", summary="Extract fields from a base64-encoded PDF resume")
async def extract_resume(request: Request):
    try:
        import pdfplumber  # type: ignore
    except ImportError:
        raise HTTPException(500, "pdfplumber not installed — run: pip install pdfplumber")

    body       = await request.json()
    pdf_base64 = body.get("pdf_base64")
    extract_mode = (body.get("mode") or "resume").strip().lower()
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

    lines     = [l.strip() for l in text.splitlines() if l.strip()]
    full_text = text.strip()

    if extract_mode == "cover_letter":
        return {"cover_letter": full_text[:15000]}

    # ── helpers ──────────────────────────────────────────────
    def find_section(headers: list[str]) -> int:
        for i, line in enumerate(lines):
            for h in headers:
                if re.match(rf"^{re.escape(h)}\s*[:\-]?\s*$", line, re.IGNORECASE):
                    return i
                if re.match(rf"^{re.escape(h)}\b", line, re.IGNORECASE) and len(line) < 40:
                    return i
        return -1

    _ALL_HEADERS = [
        "experience", "education", "skills", "projects", "certif",
        "awards", "publications", "languages", "interests", "summary",
        "objective", "profile", "work", "employment", "academic",
        "achievements", "extracurricular", "volunteer", "hobbies",
        "technical", "professional", "contact", "links", "portfolio",
    ]

    def get_section_lines(headers: list[str], max_lines: int = 20) -> list[str]:
        start = find_section(headers)
        if start < 0:
            return []
        result = []
        for line in lines[start + 1: start + 1 + max_lines]:
            if any(
                re.match(rf"^{h}\b", line, re.IGNORECASE) and len(line) < 50
                for h in _ALL_HEADERS
            ):
                break
            result.append(line)
        return result

    # ── Name ─────────────────────────────────────────────────
    full_name = ""
    for line in lines[:5]:
        if not re.search(r'[@/\\.]com|^\+?\d[\d\s\-]{8,}|http', line, re.IGNORECASE):
            if len(line.split()) >= 2 and len(line) < 60:
                full_name = line
                break
    if not full_name and lines:
        full_name = lines[0]

    # ── Email ─────────────────────────────────────────────────
    em    = re.search(r'[\w.+-]+@[\w-]+\.[\w.]+', full_text)
    email = em.group(0) if em else ""

    # ── Phone ─────────────────────────────────────────────────
    ph    = re.search(r'(\+?[\d][\d\s\-().]{9,14}\d)', full_text)
    phone = ph.group(1).strip() if ph else ""

    # ── URLs ──────────────────────────────────────────────────
    def extract_url(pattern: str) -> str:
        m = re.search(pattern, full_text, re.IGNORECASE)
        if not m:
            return ""
        url = m.group(0).strip().rstrip(".,)>")
        return ("https://" + url) if not url.startswith("http") else url

    linkedin  = extract_url(r'(?:https?://)?(?:www\.)?linkedin\.com/in/[\w\-]+')
    github    = extract_url(r'(?:https?://)?(?:www\.)?github\.com/[\w\-]+')
    leetcode  = extract_url(r'(?:https?://)?(?:www\.)?leetcode\.com/[\w\-]+')
    portfolio = extract_url(r'(?:https?://)?[\w\-]+\.(?:vercel\.app|netlify\.app|github\.io)[^\s,]*')

    # ── Location ──────────────────────────────────────────────
    location = ""
    loc_patterns = [
        r'\b([A-Z][a-zA-Z\s]+,\s*(?:Tamil Nadu|Karnataka|Maharashtra|Delhi|Telangana|'
        r'Kerala|Gujarat|Rajasthan|Punjab|UP|India|USA|UK|Canada|Australia|Germany|'
        r'France|Singapore|Remote))\b',
        r'\b([A-Z][a-z]+(?: [A-Z][a-z]+)?,\s*[A-Z][a-z]+(?: [A-Z][a-z]+)?)\b',
    ]
    header_text = "\n".join(lines[:8])
    for pat in loc_patterns:
        m = re.search(pat, header_text)
        if m:
            location = m.group(1).strip()
            break
    if not location:
        for city in [
            "Chennai","Bangalore","Bengaluru","Mumbai","Delhi","Hyderabad","Pune",
            "Kolkata","Coimbatore","Noida","Gurgaon","Gurugram","Remote",
        ]:
            for line in lines[:8]:
                if city.lower() in line.lower():
                    location = line.strip()
                    break
            if location:
                break

    # ── Skills ────────────────────────────────────────────────
    technical_skills = ""
    soft_skills_val  = ""
    skill_section = get_section_lines(
        ["skills","technical skills","technologies","tech stack",
         "core competencies","tools & technologies","programming skills"],
        max_lines=30,
    )
    if skill_section:
        raw = []
        for line in skill_section:
            m = re.match(r'^[\w\s/&]+:\s*(.+)', line)
            raw.append(m.group(1) if m else re.sub(r'^[•\-\*\u2022►▸→·]\s*', '', line))
        tokens = re.split(r'[,|;•\n]+', ", ".join(raw))
        tokens = [t.strip() for t in tokens if t.strip() and len(t.strip()) > 1]
        soft_kw = ["communication","teamwork","leadership","problem solving",
                   "time management","adaptability","critical thinking"]
        tech = [t for t in tokens if not any(k in t.lower() for k in soft_kw)]
        soft = [t for t in tokens if any(k in t.lower() for k in soft_kw)]
        technical_skills = ", ".join(tech)
        soft_skills_val  = ", ".join(soft)

    if not technical_skills:
        known = [
            "Python","Java","JavaScript","TypeScript","C\\+\\+","C#","Ruby","Go","Rust",
            "Kotlin","Swift","PHP","Dart","Scala","HTML","CSS","React","Angular","Vue",
            "Next\\.js","Node\\.js","Express","Django","Flask","Spring","FastAPI",
            "MySQL","PostgreSQL","MongoDB","SQLite","Firebase","Redis","Supabase",
            "AWS","Azure","GCP","Docker","Kubernetes","TailwindCSS","Bootstrap","Git",
        ]
        found = [t.replace("\\.", ".").replace("\\+", "+")
                 for t in known if re.search(rf'\b{t}\b', full_text, re.IGNORECASE)]
        technical_skills = ", ".join(found)

    # ── Education ─────────────────────────────────────────────
    degree_type = field_of_study = institution = ""
    edu_lines   = get_section_lines(
        ["education","academic background","academic qualifications","qualifications"],
        max_lines=15,
    )
    if edu_lines:
        for line in edu_lines:
            m = re.search(
                r'\b(B\.?Tech|B\.?E\.?|B\.?Sc\.?|B\.?C\.?A|M\.?Tech|M\.?Sc\.?|'
                r'M\.?B\.?A|M\.?C\.?A|Ph\.?D|B\.?Com|Diploma|Bachelor|Master|Associate)\b',
                line, re.IGNORECASE,
            )
            if m:
                degree_type = m.group(1)
                in_m = re.search(r'(?:in|of)\s+([A-Za-z\s&]+?)(?:\s*[-,|]\s*|\s*\d{4}|$)', line, re.IGNORECASE)
                if in_m:
                    field_of_study = in_m.group(1).strip()
                for edu_line in edu_lines:
                    if any(kw in edu_line.lower() for kw in
                           ["university","college","institute","institution","school","iit","nit","bits"]):
                        institution = edu_line.strip()
                        break
                break

    # ── Experience ────────────────────────────────────────────
    years_exp = current_title = company_name = ""
    for pat in [
        r'(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)[\s\w]{0,20}(?:of\s+)?(?:experience|exp)',
        r'(?:experience|exp)[^\d]{0,10}(\d+\.?\d*)\s*\+?\s*(?:years?|yrs?)',
    ]:
        m = re.search(pat, full_text, re.IGNORECASE)
        if m:
            years_exp = m.group(1)
            break

    exp_lines = get_section_lines(
        ["experience","work experience","professional experience",
         "employment history","internship","internships"],
        max_lines=20,
    )
    if exp_lines:
        title_pats = [
            r'^([A-Z][a-zA-Z\s]+(?:Engineer|Developer|Designer|Manager|Analyst|Intern|Lead|Architect|Consultant|Scientist|Specialist))',
            r'^([\w\s]+(?:Intern|Developer|Engineer|Designer|Analyst|Manager|Lead))',
        ]
        for line in exp_lines:
            for pat in title_pats:
                m = re.match(pat, line)
                if m:
                    current_title = m.group(1).strip()
                    at_m = re.search(r'(?:at|@|,|\|)\s*([A-Z][a-zA-Z\s]+?)(?:\s*[-|,]|\s*\d{4}|$)', line)
                    if at_m:
                        company_name = at_m.group(1).strip()
                    break
            if current_title:
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
        "resume_text":      full_text[:15000],
    }
