def compute_final_score(component_scores_dict: dict, debate_result) -> dict:
    weights = {
        "resume": 0.30,
        "github": 0.20,
        "leetcode": 0.20,
        "linkedin": 0.15,
        "role_match": 0.15
    }
    
    # Adjust weights based on debate output
    adjusted_weights = {
        "resume": weights["resume"] + debate_result.weight_adjustments.resume,
        "github": weights["github"] + debate_result.weight_adjustments.github,
        "leetcode": weights["leetcode"] + debate_result.weight_adjustments.leetcode,
        "linkedin": weights["linkedin"] + debate_result.weight_adjustments.linkedin,
        "role_match": weights["role_match"] + debate_result.weight_adjustments.role_match
    }
    
    final_score = 0.0
    calc_str_parts = []
    
    for key, weight in adjusted_weights.items():
        score = component_scores_dict.get(key, {}).get("score", 0)
        final_score += score * weight
        calc_str_parts.append(f"({score}*{weight:.2f})")
    
    # Determine confidence factor based on inconsistencies
    confidence_factor = 1.0
    if len(debate_result.inconsistencies_flagged) > 0:
        confidence_factor = max(0.90, 1.0 - (0.05 * len(debate_result.inconsistencies_flagged)))
    else: # Provide boost if perfect
        confidence_factor = min(1.05, 1.0 + 0.02)
        
    final_score = min(100.0, final_score * confidence_factor)
    
    hiring_rec = "No Hire"
    if final_score >= 85:
        hiring_rec = "Strong Hire"
    elif final_score >= 70:
        hiring_rec = "Hire"
    elif final_score >= 60:
        hiring_rec = "Borderline"

    return {
        "final_score": round(final_score, 1),
        "confidence_factor": round(confidence_factor, 2),
        "formula_calculation": f"({ ' + '.join(calc_str_parts) }) * {confidence_factor:.2f}",
        "hiring_recommendation": hiring_rec
    }
