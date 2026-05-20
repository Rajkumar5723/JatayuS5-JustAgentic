from langchain_core.runnables import RunnableLambda
from services.evaluator.agents.base import llm_component_scorer
from services.evaluator.utils.prompts import RESUME_PROMPT

async def run_resume_agent(inputs: dict):
    return await (RESUME_PROMPT | llm_component_scorer).ainvoke({
        "resume_text": inputs.get("resume_text", ""),
        "job_description": inputs.get("job_description", "")
    })

chain = RunnableLambda(run_resume_agent)
