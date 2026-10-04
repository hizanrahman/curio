import unittest

from backend.prompts.socratic_tutor import build_prompt, get_base_rules


class SocraticPromptTests(unittest.TestCase):
    def test_base_rules_require_task_anchored_questioning_and_scaffolding(self):
        rules = get_base_rules()

        self.assertIn("Never silently substitute a different entity", rules)
        self.assertIn("not as an attempt to make the student supply the answer", rules)
        self.assertIn("exact final answer", rules)
        self.assertIn("For factual and current-affairs questions", rules)
        self.assertIn("do not offload the answer-finding task", rules)
        self.assertIn("Do not disguise that same request", rules)
        self.assertIn("Do not ask \"what clue is in the question?\"", rules)
        self.assertIn("more informative than the previous turn", rules)

    def test_conceptual_strategy_scaffolds_factual_recall(self):
        prompt = build_prompt("conceptual", "general", 0, "explore")

        self.assertIn("factual identification", prompt)
        self.assertIn("without replacing the requested person, place, or event", prompt)
        self.assertIn("For a possibly changing answer you cannot confidently establish", prompt)
        self.assertIn("The probe must follow from the explanation you just gave", prompt)
        self.assertIn("not a generic opener", prompt)
        self.assertIn("connected to the student's stated task", prompt)

    def test_stuck_student_receives_more_than_a_generic_question(self):
        prompt = build_prompt("conceptual", "general", 2, "homework")

        self.assertIn("State the relevant principle and connect it directly", prompt)
        self.assertIn("focus on learning, not speed", prompt)
        self.assertIn("probe must be answerable from the", prompt)

    def test_map_objective_is_a_short_evidence_based_learning_route(self):
        rules = get_base_rules()

        self.assertIn("earliest relevant concept that is not yet mastered", rules)
        self.assertIn("exact, short phrase from the student's current message", rules)
        self.assertIn("at least two distinct turns", rules)
        self.assertIn("stop instead of asking an unnecessary question", rules)


if __name__ == "__main__":
    unittest.main()
