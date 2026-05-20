from pydantic import BaseModel, Field
from typing import Optional, Dict

class CandidateInput(BaseModel):
    job_description: str
    resume_text: str
    github_username: Optional[str] = None
    linkedin_url: Optional[str] = None
    leetcode_id: Optional[str] = None
    portfolio_url: Optional[str] = None

class ComponentScore(BaseModel):
    score: int = Field(ge=0, le=100)
    reasoning:  str
    signals: list[str] = []

class WeightAdjustments(BaseModel):
    github: float = 0.0
    leetcode: float = 0.0
    resume: float = 0.0
    linkedin: float = 0.0
    role_match: float = 0.0

class DebateOutput(BaseModel):
    panel_reasoning: str
    weight_adjustments: WeightAdjustments
    inconsistencies_flagged: list[str] = []

class EvaluationResult(BaseModel):
    hiring_recommendation: str
    final_score: float
    confidence_factor: float
    formula_calculation: str
    component_scores: Dict[str, ComponentScore]
    debate: DebateOutput
    role_matching: Dict[str, list[str]]
