"""
services/evaluator/leetcode_utils.py
======================================
Async LeetCode profile fetcher for candidate evaluation.
"""
from __future__ import annotations
import httpx

_LEETCODE_URL = "https://leetcode.com/graphql"
_HEADERS = {
    "Content-Type": "application/json",
    "Referer":      "https://leetcode.com",
    "User-Agent":   "Mozilla/5.0",
}

_PROFILE_QUERY = """query getUserProfile($username: String!) {
  matchedUser(username: $username) {
    username
    profile { ranking reputation }
    submitStatsGlobal { acSubmissionNum { difficulty count } }
    tagProblemCounts {
      advanced    { tagName problemsSolved }
      intermediate { tagName problemsSolved }
      fundamental  { tagName problemsSolved }
    }
    userCalendar { totalActiveDays }
  }
}"""

_CONTEST_QUERY = """query userContestRankingInfo($username: String!) {
  userContestRanking(username: $username) { rating attendedContestsCount }
}"""


async def fetch_leetcode(leetcode_url: str) -> tuple[dict, str]:
    """
    Returns (raw_data_dict, text_summary).
    Returns ({}, reason_string) on failure.
    """
    if not leetcode_url:
        return {}, "No LeetCode provided."

    import re
    m = re.search(r'leetcode\.com/(?:u/)?([a-zA-Z0-9_\-]+)', leetcode_url)
    if not m:
        return {}, "Could not parse LeetCode username."
    username = m.group(1)

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r1 = await client.post(
                _LEETCODE_URL,
                json={"query": _PROFILE_QUERY, "variables": {"username": username}},
                headers=_HEADERS,
            )
            r1.raise_for_status()
            user = (r1.json().get("data") or {}).get("matchedUser") or {}
            if not user:
                return {}, f"LeetCode user '{username}' not found."

            r2 = await client.post(
                _LEETCODE_URL,
                json={"query": _CONTEST_QUERY, "variables": {"username": username}},
                headers=_HEADERS,
            )
            r2.raise_for_status()
            contest = (r2.json().get("data") or {}).get("userContestRanking") or {}

        stats  = user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
        solved = {s["difficulty"]: s["count"] for s in stats}
        tags   = user.get("tagProblemCounts", {})
        all_tags = (
            tags.get("fundamental", []) +
            tags.get("intermediate", []) +
            tags.get("advanced", [])
        )
        top_tags = sorted(all_tags, key=lambda x: x.get("problemsSolved", 0), reverse=True)[:6]

        total = sum(solved.values())
        hard  = solved.get("Hard", 0)

        if total > 300 or hard > 50:
            hint = "Strong LeetCoder (75-90)"
        elif total > 100 or hard > 10:
            hint = "Decent LeetCoder (55-74)"
        elif total > 0:
            hint = "Beginner LeetCoder (30-54)"
        else:
            hint = "No problems solved (0-20)"

        raw = {
            "username":          username,
            "easy":              solved.get("Easy", 0),
            "medium":            solved.get("Medium", 0),
            "hard":              hard,
            "total":             total,
            "ranking":           user.get("profile", {}).get("ranking", "N/A"),
            "reputation":        user.get("profile", {}).get("reputation", 0),
            "active_days":       user.get("userCalendar", {}).get("totalActiveDays", 0),
            "contest_rating":    contest.get("rating", 0),
            "contests_attended": contest.get("attendedContestsCount", 0),
            "top_tags":          top_tags,
        }
        text = (
            f"Username: {username} | Total: {total} "
            f"(Easy:{raw['easy']} Medium:{raw['medium']} Hard:{hard}) | "
            f"Rank: {raw['ranking']} | Active days: {raw['active_days']} | "
            f"Contest rating: {raw.get('contest_rating', 'N/A')} "
            f"({raw.get('contests_attended', 0)} contests)\n"
            f"Top topics: {', '.join(t['tagName'] for t in top_tags[:5])}\n"
            f"Scoring hint: {hint}"
        )
        return raw, text

    except Exception as exc:
        return {}, f"LeetCode fetch failed: {exc}"
