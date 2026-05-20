"""
services/evaluator/app.py
==========================
AI Evaluation Service — Port 8001
Scores candidates using resume + GitHub + LeetCode data via Groq LLM.
Also triggers shortlisting email + test creation when score exceeds threshold.

Run with:  uvicorn services.evaluator.app:app --port 8001 --reload
"""
from __future__ import annotations
import itertools
import json
import logging
import re
import sys, os

_backend = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if _backend not in sys.path:
    sys.path.insert(0, _backend)

import requests
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from core.config import settings
from core.interview_rounds import parse_rounds_config
from core.email_utils import send_email
# ── Groq key / Old calls removed in favor of LangChain pipeline ──────


def _send_shortlist_email(candidate_email: str, candidate_name: str, job_title: str, assessment_label: str = "Shortlisting Test") -> bool:
    return send_email(
        to=candidate_email,
        subject=f"Congratulations! You've been shortlisted — {job_title}",
        body_html=f"""
<h1 style="margin:0 0 16px;font-size:24px;font-weight:700;color:#111;">
  Congratulations, {candidate_name}! 🎉
</h1>
<p style="margin:0 0 16px;font-size:16px;color:#444;line-height:1.7;">
  You have been shortlisted for the role of <strong>{job_title}</strong>.
  You will shortly receive a <strong>{assessment_label}</strong> link.
  Please complete the assessment within <strong>5 days</strong>.
</p>
<p style="margin:0;font-size:15px;color:#777;line-height:1.6;">
  Best of luck,<br><strong>The Hiresy Hiring Team</strong>
</p>""",
        stage="shortlist_notice",
    )


# ── Pydantic models ───────────────────────────────────────────
class EvalRequest(BaseModel):
    application_id:  int
    resume_text:     str
    job_description: str
    github_url:      str = ""
    linkedin_url:    str = ""
    leetcode_url:    str = ""


logger = logging.getLogger(__name__)

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Endpoints ─────────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok", "model": settings.GROQ_MODEL}


async def _run_orchestrate_evaluation(candidate_data: dict, job_description: str):
    from services.evaluator.agents.aggregator_agent import orchestrate_evaluation

    return await orchestrate_evaluation(candidate_data, job_description)


def _analyze_github(username: str):
    from services.evaluator.scrapers.github_scraper import analyze_github_data

    return analyze_github_data(username)


async def _fetch_leetcode(username: str):
    from services.evaluator.scrapers.leetcode_scraper import fetch_leetcode_profile

    return await fetch_leetcode_profile(username)


@app.post("/eval/evaluate")
async def evaluate(req: EvalRequest):
    try:
        # Extract GitHub Username
        github_username = ""
        if req.github_url:
            match = re.search(r"github\.com/([a-zA-Z0-9-]+)", req.github_url, re.IGNORECASE)
            if match:
                github_username = match.group(1)
                
        # Extract LeetCode Username
        leetcode_id = ""
        if req.leetcode_url:
            match = re.search(r"leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)", req.leetcode_url, re.IGNORECASE)
            if match:
                leetcode_id = match.group(1)

        import asyncio

        loop = asyncio.get_event_loop()
        gh_data_task = loop.run_in_executor(None, _analyze_github, github_username) if github_username else asyncio.sleep(0, result={})
        lc_data_task = _fetch_leetcode(leetcode_id) if leetcode_id else asyncio.sleep(0, result={})
        
        gh_data, lc_data = await asyncio.gather(gh_data_task, lc_data_task)

        candidate_data = {
            "resume_text": req.resume_text,
            "github_username": github_username,
            "leetcode_id": leetcode_id,
            "linkedin_url": req.linkedin_url or "Unknown",
            "github_raw": gh_data,
            "leetcode_raw": lc_data
        }

        # Run multi-agent pipeline
        result = await _run_orchestrate_evaluation(candidate_data, req.job_description)

        fs = result.get("final_score", 0)
        
        # Format data for frontend charts
        frontend_gh = {}
        if gh_data and "profile" in gh_data and gh_data["profile"]:
            p = gh_data["profile"]
            frontend_gh = {
                "username": p.get("login", ""),
                "display_name": p.get("name") or p.get("login", ""),
                "public_repos": p.get("public_repos", 0),
                "total_repos": gh_data.get("total_analyzed_repos", 0),
                "total_stars": p.get("total_stars", 0),
                "followers": p.get("followers", 0),
                "following": p.get("following", 0),
                "languages": gh_data.get("aggregated_languages_bytes", {}),
                "top_repos": [
                    {"name": r.get("name"), "stars": r.get("stars"), "forks": r.get("forks"), "size_kb": 0, "language": r.get("language"), "description": r.get("description")} 
                    for r in gh_data.get("top_repositories", [])
                ],
                "repo_types": {"original": gh_data.get("total_analyzed_repos", 0), "forked": 0}
            }

        frontend_lc = {}
        lc_display_name = ""
        if lc_data and isinstance(lc_data, dict) and "error" not in lc_data:
            stats = lc_data.get("solved_stats", [])
            easy = medium = hard = 0
            if isinstance(stats, list):
                for s in stats:
                    if isinstance(s, dict):
                        d = s.get("difficulty")
                        c = s.get("count", 0)
                        if d == "Easy": easy = c
                        elif d == "Medium": medium = c
                        elif d == "Hard": hard = c
            lc_display_name = lc_data.get("real_name") or lc_data.get("username") or leetcode_id
            frontend_lc = {
                "username": leetcode_id,
                "display_name": lc_display_name,
                "total": easy + medium + hard,
                "easy": easy,
                "medium": medium,
                "hard": hard,
                "ranking": lc_data.get("ranking")
            }

        # Build name consistency check
        gh_display_name = ""
        if frontend_gh:
            gh_display_name = frontend_gh.get("display_name") or frontend_gh.get("username") or github_username
        # Extract candidate name from resume_text (first line: "Name: ...")  
        candidate_name = ""
        for line in req.resume_text.splitlines():
            if line.lower().startswith("name:"):
                candidate_name = line.split(":", 1)[-1].strip()
                break

        def _normalize(name: str) -> str:
            return name.lower().replace("-", " ").replace("_", " ").strip()

        name_checks = []
        names_found = {}
        if candidate_name:
            names_found["Resume"] = candidate_name
        if gh_display_name:
            names_found["GitHub"] = gh_display_name
        if lc_display_name:
            names_found["LeetCode"] = lc_display_name

        # Cross-check every pair
        platforms = list(names_found.keys())
        for i in range(len(platforms)):
            for j in range(i + 1, len(platforms)):
                p1, p2 = platforms[i], platforms[j]
                n1, n2 = _normalize(names_found[p1]), _normalize(names_found[p2])
                # Simple fuzzy: one name must be substring of the other or there's a first-name match
                first1 = n1.split()[0] if n1.split() else ""
                first2 = n2.split()[0] if n2.split() else ""
                match = (n1 == n2) or (n1 in n2) or (n2 in n1) or (first1 == first2 and first1)
                name_checks.append({
                    "platforms": [p1, p2],
                    "names": [names_found[p1], names_found[p2]],
                    "match": bool(match)
                })

        # Add required backward-compatibility fields for the frontend
        debate_obj = result.get("debate", {})
        debate_dict = debate_obj if isinstance(debate_obj, dict) else (debate_obj.model_dump() if hasattr(debate_obj, 'model_dump') else {})
        result["application_id"] = req.application_id
        result["github_raw"] = frontend_gh
        result["leetcode_raw"] = frontend_lc
        result["summary"] = str(debate_dict.get("panel_reasoning", ""))
        result["inconsistencies"] = debate_dict.get("inconsistencies_flagged", [])
        result["debate_content"] = {
            "panel_reasoning": debate_dict.get("panel_reasoning", ""),
            "weight_adjustments": debate_dict.get("weight_adjustments", {}),
            "inconsistencies_flagged": debate_dict.get("inconsistencies_flagged", []),
            "name_consistency": name_checks,
            "names_found": names_found,
        }

        # Post-eval actions if above threshold
        if fs >= settings.SHORTLIST_MIN_SCORE and req.application_id:
            try:
                cand_res = requests.get(
                    f"{settings.MAIN_API_URL}/application/{req.application_id}",
                    timeout=5,
                )
                if cand_res.ok:
                    cand  = cand_res.json()
                    email = cand.get("email", "")
                    name  = cand.get("full_name", "Candidate")
                    job   = cand.get("job_name", "the position")
                    skills = cand.get("technical_skills", "General")
                    job_id = cand.get("job_id", 0)
                    configured_rounds = parse_rounds_config(cand.get("job_rounds"))
                    first_round = configured_rounds[0] if configured_rounds else "mcq"
                    assessment_kind = first_round if first_round in {"mcq", "aptitude"} else ""
                    assessment_label = (
                        "Aptitude Test"
                        if assessment_kind == "aptitude"
                        else "Shortlisting Test"
                        if assessment_kind == "mcq"
                        else "next interview round"
                    )

                    if email:
                        result["shortlist_email_sent"] = _send_shortlist_email(email, name, job, assessment_label)

                    # Create shortlisting test
                    if assessment_kind:
                        try:
                            test_res = requests.post(
                                f"{settings.test_api_url}/tests/create",
                                json={
                                    "application_id":  req.application_id,
                                    "job_id":          job_id,
                                    "candidate_name":  name,
                                    "candidate_email": email,
                                    "job_title":       job,
                                    "job_skills":      skills,
                                    "assessment_kind": assessment_kind,
                                    "duration_mins":   20,
                                    "total_questions": 10,
                                    "pass_score":      60,
                                },
                                timeout=60,
                            )
                            td = test_res.json() if test_res.ok else {}
                            result["test_created"]    = test_res.ok
                            result["test_email_sent"] = td.get("email_sent", False)
                            result["test_token"]      = td.get("token", "")
                            result["assessment_kind"] = assessment_kind
                        except Exception as te:
                            logger.warning("Auto test creation failed: %s", te)
                            result["test_created"] = False
                    else:
                        result["test_created"] = False
                        result["test_email_sent"] = False
                        result["test_token"] = ""
                        result["assessment_kind"] = ""
            except Exception as post_err:
                logger.warning("Post-eval actions failed: %s", post_err)

        return result

    except Exception as exc:
        logger.error("EVAL ERROR: %s", exc, exc_info=True)
        raise HTTPException(500, str(exc))
