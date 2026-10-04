import unittest

from backend.models.schemas import SolutionPlan
from backend.services.answer_guard import guard_answer
from backend.services.verifiers.sympy_verifier import (
    check_equivalence,
    verify_student_solution,
)


class AnswerSafetyTests(unittest.TestCase):
    def test_verifies_a_correct_one_variable_equation_answer(self):
        self.assertTrue(
            verify_student_solution(
                "3x + 7 = 22",
                "x = 5",
                "x = 5",
            )
        )

    def test_rejects_an_incorrect_answer(self):
        self.assertFalse(
            verify_student_solution(
                "3x + 7 = 22",
                "x = 4",
                "x = 5",
            )
        )

    def test_verifies_a_numeric_answer_after_worked_steps(self):
        self.assertTrue(
            verify_student_solution(
                "3x + 7 = 22",
                "I get 5.",
                "x = 5",
            )
        )

    def test_guard_rejects_a_direct_answer_leak(self):
        plan = SolutionPlan(
            final_answer="x = 5",
            key_steps=[],
            common_misconceptions=[],
            verifier="sympy",
        )

        result = guard_answer("The answer is x = 5.", plan)

        self.assertTrue(result["leaks"])

    def test_symbolic_parser_does_not_execute_python_calls(self):
        self.assertFalse(
            check_equivalence(
                "__import__('os').system('whoami')=0",
                "x=5",
            )
        )


if __name__ == "__main__":
    unittest.main()
