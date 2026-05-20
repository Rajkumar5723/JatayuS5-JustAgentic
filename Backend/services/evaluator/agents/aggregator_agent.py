from langchain_core.runnables import RunnableParallel
from services.evaluator.agents import (
    resume_agent, github_agent, leetcode_agent, 
    linkedin_agent, role_match_agent, debate_agent
)
from services.evaluator.utils.scoring_formula import compute_final_score

async def orchestrate_evaluation(candidate_data: dict, job_description: str):
    # Prepare standard input
    eval_input = {**candidate_data, "job_description": job_description}
    
    # 1. Parallel execution
    parallel_chain = RunnableParallel(
        resume=resume_agent.chain,
        github=github_agent.chain,
        leetcode=leetcode_agent.chain,
        linkedin=linkedin_agent.chain,
        role_match=role_match_agent.chain_factory(job_description)
    )
    
    component_scores = await parallel_chain.ainvoke(eval_input)
    
    # 2. Sequential Debate step
    debate_outcome = await debate_agent.chain.ainvoke({"component_scores": component_scores})
    
    # 3. Calculation
    final_output_metrics = compute_final_score(
        {k: v.model_dump() for k, v in component_scores.items()}, 
        debate_outcome
    )
    
    # Determine missing skills (Simplistic mock logic as proxy for role matching extraction)
    missing_skills = []
    jd_upper = job_description.upper()
    resume_upper = eval_input.get("resume_text", "").upper()
    keywords = ["AWS", "PYTHON", "REACT", "KUBERNETES", "GCP", "DOCKER", "FASTAPI"]
    for kw in keywords:
        if kw in jd_upper and kw not in resume_upper:
            missing_skills.append(kw)
    
    final_result = {
        "hiring_recommendation": final_output_metrics["hiring_recommendation"],
        "final_score": final_output_metrics["final_score"],
        "confidence_factor": final_output_metrics["confidence_factor"],
        "formula_calculation": final_output_metrics["formula_calculation"],
        "component_scores": component_scores,
        "debate": debate_outcome.model_dump(),
        "role_matching": {
            "missing_skills": missing_skills
        }
    }
    
    return final_result
