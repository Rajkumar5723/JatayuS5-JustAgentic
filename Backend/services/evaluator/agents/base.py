from langchain_groq import ChatGroq
from core.config import settings
from services.evaluator.schemas import ComponentScore, DebateOutput

# Shared LLM instance strictly for generating component scores
llm_component_scorer = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0.0,
    max_retries=3
).with_structured_output(ComponentScore)

# Specialized instance for the Debate agent
llm_debate_scorer = ChatGroq(
    model=settings.GROQ_MODEL,
    api_key=settings.GROQ_API_KEY,
    temperature=0.0,
    max_retries=3
).with_structured_output(DebateOutput)
