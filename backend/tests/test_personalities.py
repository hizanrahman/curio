import unittest
from itertools import product

from backend.models.schemas import SolutionPlan
from backend.prompts.socratic_tutor import PERSONALITY_TONES, build_prompt
from backend.services.answer_guard import guard_answer


class TutorPersonalityTests(unittest.TestCase):
    def test_personality_appends_only_a_tone_block(self):
        base = build_prompt("conceptual", "biology", 2, "homework")
        base_rules = base.removesuffix(f"\n{PERSONALITY_TONES['chill_senior']}\n")

        for personality, tone in PERSONALITY_TONES.items():
            with self.subTest(personality=personality):
                prompt = build_prompt("conceptual", "biology", 2, "homework", personality)
                self.assertEqual(prompt.removesuffix(f"\n{tone}\n"), base_rules)
                self.assertIn("PERSONALITY TONE:", prompt)
                self.assertTrue(any(term in tone.casefold() for term in ("never", "no emoji")))

    def test_answer_guard_still_rejects_final_answer_for_every_personality(self):
        plan = SolutionPlan(
            final_answer="x = 5",
            key_steps=["Undo the addition"],
            common_misconceptions=[],
            verifier="sympy",
            learning_objective="Solve the equation.",
            concepts=["Inverse operations", "Linear equations"],
            concept_links=[{"source": "Inverse operations", "target": "Linear equations"}],
        )
        final_answer_reply = "The answer is x = 5."

        problem_types = ("closed_form", "conceptual", "mcq", "proof_derivation", "open_ended", "code")
        for personality, problem_type in product(PERSONALITY_TONES, problem_types):
            with self.subTest(personality=personality, problem_type=problem_type):
                self.assertTrue(guard_answer(final_answer_reply, plan)["leaks"])
                prompt = build_prompt(problem_type, "mathematics", 0, "explore", personality)
                self.assertIn("Do not ask the student to provide the exact final answer", prompt)

    def test_strict_coach_tone_is_firm_without_emoji_or_shame(self):
        tone = PERSONALITY_TONES["strict_coach"].casefold()

        self.assertIn("concise, focused, and kind", tone)
        self.assertIn("no emoji", tone)
        self.assertIn("without judging ability", tone)


if __name__ == "__main__":
    unittest.main()
