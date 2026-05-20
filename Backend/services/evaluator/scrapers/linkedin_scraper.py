"""
linkedin_scraper.py
====================
Attempts to scrape a LinkedIn public profile using httpx + realistic headers.
LinkedIn heavily blocks bots, so if scraping fails the function returns a
structured fallback so the LinkedIn agent can still score based on resume data.
"""
import asyncio
import logging
import re

import httpx

logger = logging.getLogger(__name__)

_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Referer": "https://www.google.com/",
    "Cache-Control": "no-cache",
}


def _clean_html(text: str) -> str:
    """Strip HTML tags and compress whitespace."""
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:6000]


async def scrape_linkedin_profile(profile_url: str) -> str:
    """
    Attempt to fetch LinkedIn profile text via httpx.
    Returns scraped text on success, or a descriptive fallback string on failure.
    """
    if not profile_url or profile_url in ("Unknown", "candidate_linkedin_mock", ""):
        return "LinkedIn URL not provided."

    try:
        async with httpx.AsyncClient(
            headers=_HEADERS,
            follow_redirects=True,
            timeout=15,
        ) as client:
            resp = await client.get(profile_url)
            if resp.status_code == 200:
                raw = resp.text
                # Quick sanity check – LinkedIn auth wall returns very short pages
                if len(raw) > 5000:
                    cleaned = _clean_html(raw)
                    logger.info("LinkedIn scraped %d chars from %s", len(cleaned), profile_url)
                    return cleaned
                else:
                    logger.warning("LinkedIn returned short page (%d chars) — likely auth wall", len(raw))
            else:
                logger.warning("LinkedIn HTTP %d for %s", resp.status_code, profile_url)

    except Exception as exc:
        logger.warning("LinkedIn scrape failed: %s", exc)

    # Fallback: return the URL + note so the agent can still use resume data
    return (
        f"LinkedIn profile URL: {profile_url}\n"
        "Note: Profile could not be scraped (LinkedIn bot protection). "
        "Please evaluate using resume and other available signals."
    )
