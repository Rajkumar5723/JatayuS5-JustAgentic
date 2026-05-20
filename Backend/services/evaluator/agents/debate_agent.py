from langchain_core.runnables import RunnableLambda
from services.evaluator.agents.base import llm_debate_scorer
from services.evaluator.utils.prompts import DEBATE_PROMPT

async def run_debate_agent(inputs: dict):
    # Convert pydantic outputs to strings or dicts
    scores_dict = {
        k: v.model_dump() if hasattr(v, 'model_dump') else v
        for k, v in inputs.get("component_scores", {}).items()
    }
    return await (DEBATE_PROMPT | llm_debate_scorer).ainvoke({
        "component_scores": str(scores_dict)
    })

chain = RunnableLambda(run_debate_agent)
