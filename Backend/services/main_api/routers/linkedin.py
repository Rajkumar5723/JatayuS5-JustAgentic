"""
services/main_api/routers/linkedin.py
======================================
LinkedIn OAuth flow + status / disconnect endpoints.
Uses the LinkedInAccount ORM model (no raw sqlite3 calls).
"""
from __future__ import annotations
import urllib.parse

import requests
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session

from core.config import settings
from core.database import get_db
from core.models import LinkedInAccount

router = APIRouter(prefix="/linkedin", tags=["linkedin"])

_AUTH_URL = "https://www.linkedin.com/oauth/v2/authorization"
_TOKEN_URL = "https://www.linkedin.com/oauth/v2/accessToken"
_USERINFO_URL = "https://api.linkedin.com/v2/userinfo"


@router.get("/connect", summary="Start LinkedIn OAuth flow for an HR user")
def linkedin_connect(email: str):
    params = {
        "response_type": "code",
        "client_id":     settings.LI_CLIENT_ID,
        "redirect_uri":  settings.LI_REDIRECT_URI,
        "scope":         settings.LI_SCOPE,
        "state":         email,
    }
    return RedirectResponse(_AUTH_URL + "?" + urllib.parse.urlencode(params))


@router.get("/callback", summary="LinkedIn OAuth callback (handled by LinkedIn)")
def linkedin_callback(
    code: str = None,
    state: str = None,
    error: str = None,
    db: Session = Depends(get_db),
):
    frontend_base = settings.public_frontend_url + "/hrdashboard/all?linkedin="
    if error or not code:
        return RedirectResponse(frontend_base + "error")

    hr_email = state

    # Exchange code for access token
    res = requests.post(
        _TOKEN_URL,
        data={
            "grant_type":    "authorization_code",
            "code":          code,
            "redirect_uri":  settings.LI_REDIRECT_URI,
            "client_id":     settings.LI_CLIENT_ID,
            "client_secret": settings.LI_CLIENT_SECRET,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    token_data   = res.json()
    access_token = token_data.get("access_token")
    if not access_token:
        return RedirectResponse(frontend_base + "error")

    # Fetch person URN
    person_urn = ""
    info = requests.get(_USERINFO_URL, headers={"Authorization": f"Bearer {access_token}"})
    if info.status_code == 200:
        sub = info.json().get("sub", "")
        person_urn = f"urn:li:person:{sub}"

    # Upsert into DB
    existing = db.query(LinkedInAccount).filter(LinkedInAccount.hr_email == hr_email).first()
    if existing:
        existing.person_urn   = person_urn
        existing.access_token = access_token
    else:
        db.add(LinkedInAccount(
            hr_email=hr_email,
            person_urn=person_urn,
            access_token=access_token,
        ))
    db.commit()

    return RedirectResponse(frontend_base + "connected")


@router.get("/status/{email}", summary="Check if an HR user has LinkedIn connected")
def linkedin_status(email: str, db: Session = Depends(get_db)):
    row = db.query(LinkedInAccount).filter(LinkedInAccount.hr_email == email).first()
    return {"connected": bool(row)}


@router.delete("/disconnect/{email}", summary="Disconnect LinkedIn for an HR user")
def linkedin_disconnect(email: str, db: Session = Depends(get_db)):
    db.query(LinkedInAccount).filter(LinkedInAccount.hr_email == email).delete()
    db.commit()
    return {"message": "Disconnected"}


@router.get("/profile", summary="Scrape a LinkedIn public profile")
def get_linkedin_profile(url: str):
    try:
        from linkedin_scraper import scrape_linkedin  # type: ignore
        data = scrape_linkedin(url)
        return {"success": bool(data.get("name")), "data": data}
    except Exception as exc:
        return {"success": False, "data": {}, "error": str(exc)}
