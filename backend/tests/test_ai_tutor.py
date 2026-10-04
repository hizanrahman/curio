import json
import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from backend.models.schemas import TutorResponse
from backend.services.ai_tutor import (
    TutorConfigurationError,
    TutorProviderError,
    _ensure_guiding_question,
    generate_tutor_response,
)


class SocraticTutorRequestTests(unittest.TestCase):
    def test_reports_provider_quota_as_actionable_unavailable_error(self):
        error = TutorProviderError(429)

        self.assertIn("quota is exhausted", str(error))
        self.assertIn("available model", str(error))

    def test_reports_missing_ai_configuration_separately(self):
        with (
            patch("backend.services.ai_tutor._get_client", return_value=None),
            self.assertRaises(TutorConfigurationError),
        ):
            generate_tutor_response("problem", "attempt", 0, "explore")

    def test_wraps_plain_text_provider_response_and_adds_a_tutor_question(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content="Try undoing addition first."))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response("problem", "attempt", 0, "explore")

        self.assertEqual(
            result.message,
            "Try undoing addition first. What do you get when you apply that step to this problem?",
        )
        self.assertEqual(result.response_type, "question")
        self.assertEqual(result.concept_updates, [])
        self.assertEqual(result.mastery_evidence, [])

    def test_does_not_show_provider_safety_metadata_as_tutor_reply(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(
                message=SimpleNamespace(content="User Safety: safe Response Safety: safe")
            )]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response(
                "Why does a metal spoon feel colder than wood?",
                "I am not sure",
                0,
                "explore",
                problem_type="conceptual",
            )

        self.assertNotIn("Safety", result.message)
        self.assertNotIn("safe", result.message.lower())
        self.assertIn("What part of the idea", result.message)

    def test_removes_leading_safety_metadata_but_keeps_actual_tutor_message(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(
                content="User Safety: safe Response Safety: safe Metal transfers heat faster. Which material transfers heat faster?"
            ))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response("problem", "attempt", 0, "explore")

        self.assertEqual(
            result.message,
            "Metal transfers heat faster. Which material transfers heat faster?",
        )

    def test_extracts_json_response_from_markdown_and_surrounding_text(self):
        response_data = {
            "response_type": "hint",
            "message": "Try balancing both sides. What would you undo first?",
            "hint_level": 1,
            "concept_updates": [],
            "mastery_evidence": [],
        }
        content = f"Response:\n```json\n{json.dumps(response_data)}\n```\n"
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response("problem", "attempt", 1, "explore")

        self.assertEqual(result.response_type, "hint")
        self.assertEqual(result.message, response_data["message"])

    def test_normalizes_partial_json_response_without_failing_the_turn(self):
        response_data = {
            "content": "Use the inverse operation. What would undo the addition?",
            "hint_level": "invalid",
            "concept_updates": [{"concept": "", "status": "unknown", "evidence": ""}],
            "session_completed": True,
            "verified": True,
            "reward_points": 100,
        }
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(response_data)))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response("problem", "attempt", 0, "explore")

        self.assertEqual(result.message, response_data["content"])
        self.assertEqual(result.response_type, "question")
        self.assertEqual(result.concept_updates, [])
        self.assertFalse(result.session_completed)
        self.assertFalse(result.verified)
        self.assertEqual(result.reward_points, 0)

    def test_returns_safe_guided_question_for_malformed_json(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content='{"response_type":'))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response(
                "problem",
                "attempt",
                0,
                "explore",
                problem_type="code",
            )

        self.assertEqual(result.response_type, "question")
        self.assertIn("What do you expect the code to do", result.message)
        self.assertEqual(result.concept_updates, [])

    def test_returns_safe_guided_question_when_response_has_no_message(self):
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps({"response_type": "question"})))]
        )
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response(
                "problem",
                "attempt",
                0,
                "explore",
                problem_type="conceptual",
            )

        self.assertEqual(result.response_type, "question")
        self.assertIn("What part of the idea", result.message)
        self.assertEqual(result.concept_updates, [])

    def test_returns_safe_guided_question_for_empty_or_non_text_provider_content(self):
        for content in (None, [{"type": "image"}]):
            completion = SimpleNamespace(
                choices=[SimpleNamespace(message=SimpleNamespace(content=content))]
            )
            client = SimpleNamespace(
                chat=SimpleNamespace(
                    completions=SimpleNamespace(create=Mock(return_value=completion))
                )
            )
            with patch("backend.services.ai_tutor._get_client", return_value=client):
                result = generate_tutor_response(
                    "problem",
                    "attempt",
                    0,
                    "explore",
                    problem_type="open_ended",
                )

            self.assertIn("Which part of the prompt", result.message)

    def test_returns_safe_question_if_provider_returns_no_choices(self):
        completion = SimpleNamespace(choices=[])
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=Mock(return_value=completion))
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response("problem", "attempt", 0, "explore")

        self.assertIn("Which operation would you undo first?", result.message)

    def test_adds_a_task_appropriate_question_when_model_omits_one(self):
        response = TutorResponse(
            response_type="hint",
            message=(
                "The Chief Minister leads a state government. "
                "For a current officeholder, check the official source."
            ),
            hint_level=1,
            concept_updates=[],
            mastery_evidence=[],
        )

        result = _ensure_guiding_question(response, "conceptual", "Who is the Chief Minister of Kerala?")

        self.assertTrue(result.message.endswith(
            "What part of that explanation helps you reason about the question you asked?"
        ))

    def test_does_not_add_a_second_question_when_model_already_asks_one(self):
        response = TutorResponse(
            response_type="question",
            message="Which operation would undo the multiplication?",
            hint_level=0,
            concept_updates=[],
            mastery_evidence=[],
        )

        result = _ensure_guiding_question(response, "closed_form")

        self.assertEqual(result.message, "Which operation would undo the multiplication?")

    def test_factual_clarification_keeps_task_and_socratic_rules_in_request(self):
        response_data = {
            "response_type": "hint",
            "message": (
                "I understand you mean the Chief Minister of Kerala. "
                "That role leads the state government. Which responsibility "
                "helps explain what the office does?"
            ),
            "hint_level": 1,
            "concept_updates": [],
            "mastery_evidence": [],
            "verifier_status": None,
        }
        completion = SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(content=json.dumps(response_data))
                )
            ]
        )
        create_completion = Mock(return_value=completion)
        client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(create=create_completion)
            )
        )

        with patch("backend.services.ai_tutor._get_client", return_value=client):
            result = generate_tutor_response(
                problem_text="Who is the Chief Minister of Kerala?",
                student_step="who is he",
                hint_level=1,
                mode="explore",
                misconceptions=[],
                concepts=["Chief Minister", "Kerala government"],
                problem_type="conceptual",
                solution_plan={
                    "key_steps": ["Identify what CM means", "Verify a current officeholder"],
                    "common_misconceptions": [],
                },
                subject="general",
                conversation_history=[
                    {"role": "user", "content": "who is he"},
                    {"role": "tutor", "content": "What would you try first?"},
                ],
                topic="civics",
                concept_progress=[{
                    "name": "Kerala government",
                    "status": "developing",
                    "evidence_count": 1,
                }],
            )

        self.assertEqual(result.response_type, "hint")
        messages = create_completion.call_args.kwargs["messages"]
        self.assertIn("never substitute a place", messages[0]["content"])
        self.assertIn("Do not ask for the final answer", messages[0]["content"])
        self.assertIn("Never offload the requested answer-finding task", messages[0]["content"])
        self.assertIn("exactly one focused", messages[0]["content"])
        self.assertIn("Do not ask for the", messages[1]["content"])
        self.assertIn("probe must not ask about the", messages[1]["content"])
        self.assertIn("Do not ask the student to guess which one was adopted", messages[1]["content"])
        self.assertIn("If the student says", messages[1]["content"])
        self.assertIn("never ask what clue is in the question", messages[0]["content"])
        self.assertIn("Who is the Chief Minister of Kerala?", messages[1]["content"])
        self.assertIn("Topic: civics", messages[1]["content"])
        self.assertIn('"current_student_input": "who is he"', messages[1]["content"])
        self.assertIn('"status": "developing"', messages[1]["content"])


if __name__ == "__main__":
    unittest.main()
