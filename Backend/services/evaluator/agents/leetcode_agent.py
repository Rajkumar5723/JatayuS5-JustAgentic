from langchain_core.runnables import RunnableLambda
from services.evaluator.agents.base import llm_component_scorer
from services.evaluator.utils.prompts import LEETCODE_PROMPT
from services.evaluator.scrapers.leetcode_scraper import fetch_leetcode_profile

async def run_leetcode_agent(inputs: dict):
    lc_data = inputs.get("leetcode_raw", {})
    
    return await (LEETCODE_PROMPT | llm_component_scorer).ainvoke({
        "leetcode_id": str(lc_data), # Provide the actual graphQL metrics into the prompt
        "job_description": inputs.get("job_description", "")
    })

chain = RunnableLambda(run_leetcode_agent)
