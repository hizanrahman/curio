from pydantic import BaseModel, Field
from typing import List, Optional, Literal

class ConceptUpdate(BaseModel):
    concept: str = Field(min_length=1, max_length=100)
    status: Literal["mastered", "developing", "needs_practice", "practicing", "not_assessed"]
    evidence: str = Field(min_length=1, max_length=500)


class ConceptLink(BaseModel):
    source: str = Field(min_length=1, max_length=100)
    target: str = Field(min_length=1, max_length=100)


class TutorResponse(BaseModel):
    response_type: Literal[
        "question",
        "hint",
        "acknowledgement",
        "verification",
        "completion"
    ]
    message: str
    hint_level: int = Field(ge=0, le=3)
    concept_updates: List[ConceptUpdate]
    mastery_evidence: List[str]
    verifier_status: Optional[str] = None
    session_completed: bool = False
    verified: bool = False
    independent_solve: bool = False
    reward_points: int = 0

class SolutionPlan(BaseModel):
    final_answer: Optional[str] = None
    key_steps: List[str]
    common_misconceptions: List[str]
    rubric: Optional[List[dict]] = None
    verifier: Literal["sympy", "units", "code_runner", "llm", "none"]
    learning_objective: Optional[str] = Field(default=None, max_length=300)
    concepts: List[str] = Field(default_factory=list, max_length=12)
    concept_links: List[ConceptLink] = Field(default_factory=list, max_length=24)
    transfer_problem: Optional[str] = Field(default=None, max_length=2000)
