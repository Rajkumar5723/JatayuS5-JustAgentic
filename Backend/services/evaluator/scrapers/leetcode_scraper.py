import httpx
import logging

logger = logging.getLogger(__name__)

LEETCODE_GRAPHQL_URL = "https://leetcode.com/graphql"
HEADERS = {
    "Content-Type": "application/json",
    "Referer": "https://leetcode.com",
    "User-Agent": "Mozilla/5.0"
}

PROFILE_QUERY = """
query getUserProfile($username: String!) {
    matchedUser(username: $username) {
        username
        profile { ranking reputation }
        submitStatsGlobal { acSubmissionNum { difficulty count } }
        tagProblemCounts {
            advanced { tagName problemsSolved }
            intermediate { tagName problemsSolved }
            fundamental { tagName problemsSolved }
        }
        userCalendar { activeYears totalActiveDays submissionCalendar }
        submitStats {
            totalSubmissionNum { difficulty count submissions }
            acSubmissionNum { difficulty count submissions }
        }
    }
}
"""

CONTEST_QUERY = """
query userContestRankingInfo($username: String!) {
    userContestRanking(username: $username) {
        rating
        attendedContestsCount
    }
}
"""

async def fetch_leetcode_profile(username: str) -> dict:
    if not username or username == "Unknown" or username == "candidate_leetcode_mock":
        return {"error": "Invalid LeetCode username"}
        
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp1 = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": PROFILE_QUERY, "variables": {"username": username}},
                headers=HEADERS
            )
            resp1.raise_for_status()
            data = resp1.json().get("data", {})
            user = data.get("matchedUser")
            
            if not user:
                return {"error": "User not found"}
                
            resp2 = await client.post(
                LEETCODE_GRAPHQL_URL,
                json={"query": CONTEST_QUERY, "variables": {"username": username}},
                headers=HEADERS
            )
            resp2.raise_for_status()
            contest_data = resp2.json().get("data", {}).get("userContestRanking") or {}
            
            # Formatted Output
            stats = user.get("submitStatsGlobal", {}).get("acSubmissionNum", [])
            tag_data = user.get("tagProblemCounts", {})
            calendar = user.get("userCalendar", {})
            
            return {
                "ranking": user.get("profile", {}).get("ranking"),
                "reputation": user.get("profile", {}).get("reputation"),
                "solved_stats": stats,
                "tags": tag_data,
                "calendar": calendar,
                "contest_rating": contest_data.get("rating"),
                "contests_attended": contest_data.get("attendedContestsCount")
            }
    except Exception as e:
        logger.error(f"LeetCode fetch failed: {e}")
        return {"error": str(e)}
