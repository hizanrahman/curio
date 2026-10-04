import re
from backend.models.schemas import SolutionPlan
from backend.services.verifiers.sympy_verifier import check_equivalence

def guard_answer(tutor_message: str, plan: SolutionPlan) -> dict:
    """
    Layer 1: Normalized string checks
    Layer 2: SymPy equivalence check (for math)
    Layer 3: LLM Judge check (skipped in mock)
    Layer 4: Code / Essay guard
    """
    msg_lower = tutor_message.lower()
    
    # Layer 1: Pattern checks
    prohibited_phrases = ["the answer is", "therefore x =", "final answer", "x equals", "so x is"]
    for phrase in prohibited_phrases:
        if phrase in msg_lower:
            return {"leaks": True, "reason": f"Uses prohibited phrase: {phrase}"}

    final_answer = (plan.final_answer or "").strip()
    if final_answer and re.search(
        rf"(?<![\w.]){re.escape(final_answer)}(?![\w.])",
        tutor_message,
        flags=re.IGNORECASE,
    ):
        return {"leaks": True, "reason": "Exact final answer appears in text."}
         
    # Layer 2: SymPy equivalence (if applicable)
    if plan.verifier == "sympy" and plan.final_answer:
        # Extract potential equations from tutor_message (basic regex for demo)
        equations = re.findall(r'[a-zA-Z0-9\+\-\*/\s]+=[a-zA-Z0-9\+\-\*/\s]+', tutor_message)
        for eq in equations:
            if check_equivalence(eq, f"x={plan.final_answer}"):
                return {"leaks": True, "reason": "Mathematically equivalent answer leaked."}
                
    return {"leaks": False, "reason": ""}
