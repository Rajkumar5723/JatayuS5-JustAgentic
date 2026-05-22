from __future__ import annotations

import logging
import re
from datetime import datetime
from typing import Any

import requests

from core.config import settings

logger = logging.getLogger(__name__)

MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
EMPTY_URL_VALUES = {"", "na", "n/a", "none", "null", "-", "--"}


def clean_profile_url(value: str | None) -> str:
    cleaned = str(value or "").strip()
    return "" if cleaned.lower() in EMPTY_URL_VALUES else cleaned


def extract_username(pattern: str, value: str | None) -> str:
    cleaned = clean_profile_url(value)
    match = re.search(pattern, cleaned, re.IGNORECASE)
    return match.group(1).strip("/") if match else ""


def fetch_github_light(github_url: str | None) -> dict[str, Any]:
    username = extract_username(r"github\.com/([a-zA-Z0-9-]+)", github_url)
    if not username:
        return {}
    headers = {"Authorization": f"token {settings.GITHUB_TOKEN}"} if settings.GITHUB_TOKEN else {}
    try:
        profile_res = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=8)
        repos_res = requests.get(
            f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=100",
            headers=headers,
            timeout=10,
        )
        profile = profile_res.json() if profile_res.ok else {}
        repos_payload = repos_res.json() if repos_res.ok else []
        repos = repos_payload if isinstance(repos_payload, list) else []

        total_stars = sum(int(repo.get("stargazers_count") or 0) for repo in repos)
        total_forks = sum(int(repo.get("forks_count") or 0) for repo in repos)
        languages: dict[str, int] = {}
        for repo in repos:
            lang = repo.get("language") or "Other"
            languages[lang] = languages.get(lang, 0) + 1

        commit_by_month = {month: 0 for month in MONTHS}
        events_res = requests.get(
            f"https://api.github.com/users/{username}/events?per_page=100",
            headers=headers,
            timeout=8,
        )
        if events_res.ok:
            events_payload = events_res.json()
            if isinstance(events_payload, list):
                for event in events_payload:
                    if event.get("type") != "PushEvent" or not event.get("created_at"):
                        continue
                    created_at = datetime.fromisoformat(str(event["created_at"]).replace("Z", "+00:00"))
                    month = created_at.strftime("%b")
                    commit_by_month[month] = commit_by_month.get(month, 0) + int(
                        (event.get("payload") or {}).get("size") or 1
                    )

        return {
            "username": username,
            "display_name": profile.get("name") or profile.get("login") or username,
            "public_repos": profile.get("public_repos", len(repos)),
            "total_repos": len(repos),
            "total_stars": total_stars,
            "total_forks": total_forks,
            "followers": profile.get("followers", 0),
            "following": profile.get("following", 0),
            "languages": languages,
            "commit_activity": [{"month": month, "commits": commit_by_month.get(month, 0)} for month in MONTHS],
            "top_repos": [
                {
                    "name": repo.get("name"),
                    "stars": repo.get("stargazers_count", 0),
                    "forks": repo.get("forks_count", 0),
                    "language": repo.get("language"),
                    "description": repo.get("description") or "",
                }
                for repo in sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:8]
            ],
            "repo_types": {
                "original": sum(1 for repo in repos if not repo.get("fork")),
                "forked": sum(1 for repo in repos if repo.get("fork")),
            },
        }
    except Exception as exc:
        logger.warning("Light GitHub fetch failed for %s: %s", username, exc)
        return {"username": username, "display_name": username}


def fetch_leetcode_light(leetcode_url: str | None) -> dict[str, Any]:
    username = extract_username(r"leetcode\.com/(?:u/)?([a-zA-Z0-9_-]+)", leetcode_url)
    if not username:
        return {}
    query = """
query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile { ranking reputation }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    userCalendar { totalActiveDays }
  }
  userContestRanking(username: $username) {
    rating
    attendedContestsCount
  }
}
"""
    try:
        response = requests.post(
            "https://leetcode.com/graphql",
            json={"query": query, "variables": {"username": username}},
            headers={
                "Content-Type": "application/json",
                "Referer": "https://leetcode.com",
                "User-Agent": "Mozilla/5.0",
            },
            timeout=12,
        )
        response.raise_for_status()
        data = response.json().get("data") or {}
        user = data.get("matchedUser") or {}
        if not user:
            return {"username": username, "display_name": username, "total": 0, "easy": 0, "medium": 0, "hard": 0}
        stats = user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
        solved = {item.get("difficulty"): int(item.get("count") or 0) for item in stats}
        total = solved.get("All", 0) or sum(count for key, count in solved.items() if key != "All")
        contest = data.get("userContestRanking") or {}
        return {
            "username": username,
            "display_name": user.get("username") or username,
            "total": total,
            "easy": solved.get("Easy", 0),
            "medium": solved.get("Medium", 0),
            "hard": solved.get("Hard", 0),
            "ranking": (user.get("profile") or {}).get("ranking"),
            "reputation": (user.get("profile") or {}).get("reputation", 0),
            "active_days": (user.get("userCalendar") or {}).get("totalActiveDays", 0),
            "contest_rating": contest.get("rating"),
            "contests_attended": contest.get("attendedContestsCount"),
        }
    except Exception as exc:
        logger.warning("Light LeetCode fetch failed for %s: %s", username, exc)
        return {"username": username, "display_name": username, "total": 0, "easy": 0, "medium": 0, "hard": 0}


def normalize_eval_profiles(
    eval_payload: dict[str, Any] | None,
    *,
    github_url: str | None = "",
    leetcode_url: str | None = "",
) -> dict[str, Any]:
    payload = dict(eval_payload or {})
    github_url = clean_profile_url(github_url or payload.get("github_url"))
    leetcode_url = clean_profile_url(leetcode_url or payload.get("leetcode_url"))
    if github_url:
        payload["github_url"] = github_url
    if leetcode_url:
        payload["leetcode_url"] = leetcode_url

    github_raw = payload.get("github_raw") if isinstance(payload.get("github_raw"), dict) else {}
    if github_url and not github_raw.get("username"):
        github_raw = fetch_github_light(github_url)
    payload["github_raw"] = github_raw or {}

    leetcode_raw = payload.get("leetcode_raw") if isinstance(payload.get("leetcode_raw"), dict) else {}
    if leetcode_url and not leetcode_raw.get("username"):
        leetcode_raw = fetch_leetcode_light(leetcode_url)
    payload["leetcode_raw"] = leetcode_raw or {}
    payload.setdefault("component_scores", {})
    return payload
