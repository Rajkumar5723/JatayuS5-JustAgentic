from sentence_transformers import SentenceTransformer
import faiss
import numpy as np
from langchain_core.runnables import RunnableLambda
from services.evaluator.schemas import ComponentScore
import asyncio

# Load the model synchronously at module load time (in prod, load this lazily or explicitly on startup)
model = SentenceTransformer('all-MiniLM-L6-v2')

def create_role_match_chain(job_description: str):
    jd_embedding = model.encode([job_description])
    jd_norm = jd_embedding / np.linalg.norm(jd_embedding, axis=1, keepdims=True)
    
    async def run_role_match(inputs: dict):
        resume_text = inputs.get("resume_text", "")
        if not resume_text:
            return ComponentScore(score=0, reasoning="No resume text provided.", signals=["Missing resume"])
        
        # Run potentially blocking operations in a default executor
        loop = asyncio.get_event_loop()
        
        def _compute():
            resume_embedding = model.encode([resume_text])
            res_norm = resume_embedding / np.linalg.norm(resume_embedding, axis=1, keepdims=True)
            
            index = faiss.IndexFlatIP(jd_norm.shape[1])
            index.add(jd_norm)
            
            D, I = index.search(res_norm, 1)
            similarity = D[0][0]
            score = max(0, min(100, int(similarity * 100)))
            return score, similarity

        score, similarity = await loop.run_in_executor(None, _compute)
        
        return ComponentScore(
            score=score,
            reasoning=f"Cosine similarity between resume and job description is {similarity:.2f}.",
            signals=["Vector match completed locally using FAISS."]
        )
        
    return RunnableLambda(run_role_match)

def chain_factory(job_description: str):
    return create_role_match_chain(job_description)
