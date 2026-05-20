from langchain_core.runnables import RunnableLambda
from services.evaluator.agents.base import llm_component_scorer
from services.evaluator.utils.prompts import LINKEDIN_PROMPT
from services.evaluator.scrapers.linkedin_scraper import scrape_linkedin_profile


async def run_linkedin_agent(inputs: dict):
    linkedin_url = inputs.get("linkedin_url", "")
    resume_text = inputs.get("resume_text", "")

    # Attempt to scrape the public LinkedIn profile
    scraped_text = await scrape_linkedin_profile(linkedin_url)

    # Build context: use scraped text; always append resume as fallback context
    profile_context = scraped_text
    if resume_text:
        profile_context += f"\n\n--- Candidate Resume (for additional context) ---\n{resume_text[:3000]}"

    return await (LINKEDIN_PROMPT | llm_component_scorer).ainvoke({
        "linkedin_url": profile_context,
        "job_description": inputs.get("job_description", "")
    })


chain = RunnableLambda(run_linkedin_agent)
