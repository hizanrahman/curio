def prompt_additions(problem_type: str) -> str:
    if problem_type == "closed_form":
        return "Ensure all mathematical operations follow order of operations. Ask student to identify the next operation."
    return ""

def seed_concepts() -> list:
    return ["variables", "equation_manipulation", "inverse_operations", "verification"]

def guard_strategy() -> str:
    return "sympy_equivalence"

def render_hints() -> str:
    return "math"
