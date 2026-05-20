from langchain_core.runnables import RunnableLambda
from services.evaluator.agents.base import llm_component_scorer
from services.evaluator.utils.prompts import GITHUB_PROMPT
import asyncio
from services.evaluator.scrapers.github_scraper import analyze_github_data

async def run_github_agent(inputs: dict):
    gh_data = inputs.get("github_raw", {})
    
    return await (GITHUB_PROMPT | llm_component_scorer).ainvoke({
        "github_username": str(gh_data)[:2000],  # Supply the actual JSON data dumped as string
        "job_description": inputs.get("job_description", "")
    })

chain = RunnableLambda(run_github_agent)
