"""
services/evaluator/github_utils.py
====================================
Fetch and summarise a GitHub profile for candidate evaluation.
"""
from __future__ import annotations
import requests
from datetime import datetime, timezone
from core.config import settings


def fetch_github(github_url: str) -> tuple[dict, str]:
    """
    Returns (raw_data_dict, text_summary).
    Returns ({}, reason_string) on failure.
    """
    if not github_url:
        return {}, "No GitHub provided."

    import re
    m = re.search(r'github\.com/([a-zA-Z0-9\-]+)', github_url)
    if not m:
        return {}, "Could not parse GitHub username."
    username = m.group(1)

    headers = {"Authorization": f"token {settings.GITHUB_TOKEN}"} if settings.GITHUB_TOKEN else {}

    try:
        profile   = requests.get(f"https://api.github.com/users/{username}", headers=headers, timeout=8).json()
        repos_res = requests.get(
            f"https://api.github.com/users/{username}/repos?sort=pushed&per_page=100",
            headers=headers, timeout=10,
        )
        repos = repos_res.json() if repos_res.ok and isinstance(repos_res.json(), list) else []

        lang_counts = {}
        total_stars = total_forks = total_size = 0
        repo_types  = {"original": 0, "forked": 0}
        for r in repos:
            lang = r.get("language") or "Other"
            lang_counts[lang] = lang_counts.get(lang, 0) + 1
            total_stars += r.get("stargazers_count", 0)
            total_forks += r.get("forks_count", 0)
            total_size  += r.get("size", 0)
            if r.get("fork"):
                repo_types["forked"] += 1
            else:
                repo_types["original"] += 1

        top_repos = sorted(repos, key=lambda r: r.get("stargazers_count", 0), reverse=True)[:8]
        top_langs = sorted(lang_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        commit_by_month: dict[str, int] = {}
        events_res = requests.get(
            f"https://api.github.com/users/{username}/events?per_page=100",
            headers=headers, timeout=8,
        )
        if events_res.ok:
            for ev in events_res.json():
                if ev.get("type") == "PushEvent":
                    dt = datetime.fromisoformat(ev["created_at"].replace("Z", "+00:00"))
                    mk = dt.strftime("%b")
                    commit_by_month[mk] = commit_by_month.get(mk, 0) + ev.get("payload", {}).get("size", 1)

        months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
        commit_activity = [{"month": m, "commits": commit_by_month.get(m, 0)} for m in months]

        orig = repo_types["original"]
        if total_stars > 50 or orig > 15:
            hint = "Strong GitHub (75-90)"
        elif total_stars > 10 or orig > 5:
            hint = "Decent GitHub (55-74)"
        elif repos:
            hint = "Weak GitHub (30-54)"
        else:
            hint = "Empty GitHub (10-29)"

        raw = {
            "username":      username,
            "name":          profile.get("name", username),
            "bio":           profile.get("bio", ""),
            "followers":     profile.get("followers", 0),
            "following":     profile.get("following", 0),
            "total_repos":   len(repos),
            "public_repos":  profile.get("public_repos", len(repos)),
            "languages":     lang_counts,
            "total_stars":   total_stars,
            "total_forks":   total_forks,
            "total_size_mb": round(total_size / 1024, 1),
            "repo_types":    repo_types,
            "commit_activity": commit_activity,
            "top_repos": [
                {
                    "name":        r["name"],
                    "stars":       r.get("stargazers_count", 0),
                    "forks":       r.get("forks_count", 0),
                    "language":    r.get("language", "?"),
                    "description": (r.get("description") or "")[:70],
                    "size_kb":     r.get("size", 0),
                    "fork":        r.get("fork", False),
                }
                for r in top_repos
            ],
        }
        text = (
            f"Username: {username} | Repos: {len(repos)} | Stars: {total_stars} | "
            f"Forks: {total_forks} | Followers: {profile.get('followers', 0)} | "
            f"Original: {orig} | Forked: {repo_types['forked']}\n"
            f"Top languages: {', '.join(f'{l}({c})' for l, c in top_langs)}\n"
            f"Top repos: " + " | ".join(f"{r['name']}(⭐{r.get('stargazers_count',0)})" for r in top_repos[:5]) +
            f"\nScoring hint: {hint}"
        )
        return raw, text

    except Exception as exc:
        return {}, f"GitHub fetch failed: {exc}"
