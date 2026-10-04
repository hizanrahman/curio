import ast
import operator
import math
import re

import sympy


_BINARY_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
}
_UNARY_OPERATORS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def _safe_expression(node: ast.AST):
    if isinstance(node, ast.Constant) and isinstance(node.value, int) and not isinstance(node.value, bool):
        if abs(node.value) > 10**9:
            raise ValueError("Number is outside the supported range.")
        return sympy.Integer(node.value)
    if isinstance(node, ast.Constant) and isinstance(node.value, float):
        if not math.isfinite(node.value) or abs(node.value) > 10**9:
            raise ValueError("Number is outside the supported range.")
        return sympy.Float(node.value)
    if isinstance(node, ast.Name):
        return sympy.Symbol(node.id)
    if isinstance(node, ast.BinOp) and type(node.op) in _BINARY_OPERATORS:
        left = _safe_expression(node.left)
        right = _safe_expression(node.right)
        if isinstance(node.op, ast.Pow):
            if not right.is_Integer or abs(int(right)) > 12:
                raise ValueError("Exponent is outside the supported range.")
        result = _BINARY_OPERATORS[type(node.op)](left, right)
        if result.is_Integer and int(result).bit_length() > 4096:
            raise ValueError("Expression result is outside the supported range.")
        if sympy.count_ops(result) > 100:
            raise ValueError("Expression is too complex.")
        return result
    if isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY_OPERATORS:
        return _UNARY_OPERATORS[type(node.op)](_safe_expression(node.operand))
    raise ValueError("Unsupported expression.")


def _parse_side(expression: str):
    if len(expression) > 256:
        raise ValueError("Expression is too long.")
    normalized = expression.strip().replace("^", "**")
    normalized = re.sub(r"(?<=\d)\s*(?=[A-Za-z(])", "*", normalized)
    normalized = re.sub(r"(?<=\))\s*(?=[A-Za-z(])", "*", normalized)
    tree = ast.parse(normalized, mode="eval")
    if sum(1 for _ in ast.walk(tree)) > 100:
        raise ValueError("Expression is too complex.")
    return _safe_expression(tree.body)


def _equation_parts(text: str) -> tuple[str, str] | None:
    match = re.search(
        r"([A-Za-z0-9_+\-*/^().\s]{1,256}=[A-Za-z0-9_+\-*/^().\s]{1,256})",
        text,
    )
    if not match:
        return None
    left, right = match.group(1).split("=", 1)
    return left.strip(), right.strip()

def check_equivalence(eq1_str: str, eq2_str: str) -> bool:
    """
    Check if two equation strings are mathematically equivalent.
    """
    try:
        # Very basic parsing for a full application
        parts1 = _equation_parts(eq1_str)
        parts2 = _equation_parts(eq2_str)
        if not parts1 or not parts2:
            return False
        lhs1, rhs1 = parts1
        lhs2, rhs2 = parts2
        expr1 = _parse_side(lhs1) - _parse_side(rhs1)
        expr2 = _parse_side(lhs2) - _parse_side(rhs2)
        if expr2 == 0:
            return False
        
        # Check if expr1 is a non-zero constant multiple of expr2
        ratio = sympy.simplify(expr1 / expr2)
        return ratio.is_constant() and ratio != 0
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError, OverflowError, AttributeError):
        return False


def verify_student_solution(problem_text: str, student_text: str, final_answer: str | None) -> bool:
    if not final_answer or len(problem_text) > 8000 or len(student_text) > 4000:
        return False
    problem_equation = _equation_parts(problem_text)
    if not problem_equation:
        return False
    try:
        residual = _parse_side(problem_equation[0]) - _parse_side(problem_equation[1])
        symbols = residual.free_symbols
        if len(symbols) != 1:
            return False
        variable = next(iter(symbols))

        student_equation = _equation_parts(student_text)
        if student_equation:
            left = _parse_side(student_equation[0])
            right = _parse_side(student_equation[1])
            if left == variable:
                student_answer = right
            elif right == variable:
                student_answer = left
            else:
                return False
        else:
            cleaned_student_text = student_text.rstrip(" \t\r\n.!?;")
            final_number = re.search(r"[-+]?\d+(?:\.\d+)?(?:\s*/\s*\d+)?\s*$", cleaned_student_text)
            if not final_number:
                return False
            student_answer = _parse_side(final_number.group(0))

        expected_equation = _equation_parts(final_answer)
        if expected_equation:
            expected_left = _parse_side(expected_equation[0])
            expected_right = _parse_side(expected_equation[1])
            if expected_left == variable:
                expected_answer = expected_right
            elif expected_right == variable:
                expected_answer = expected_left
            else:
                return False
        else:
            expected_answer = _parse_side(final_answer)

        return (
            sympy.simplify(student_answer - expected_answer) == 0
            and sympy.simplify(residual.subs(variable, student_answer)) == 0
        )
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
        return False
