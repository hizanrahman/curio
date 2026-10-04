import json
import unittest
from types import SimpleNamespace
from uuid import UUID
from unittest.mock import AsyncMock, patch

from fastapi import HTTPException
from fastapi.testclient import TestClient

from backend.api import sessions
from backend.api.sessions import (
    MessageRequest,
    SessionCreate,
    _validate_concept_updates,
    create_session,
    get_session,
    send_message,
)
from backend.models.schemas import ConceptLink, ConceptUpdate, SolutionPlan, TutorResponse
from backend.prompts.socratic_tutor import build_prompt
from backend.services.ai_tutor import TutorProviderError
from backend.services.authentication import get_current_user
from backend.services import solution_planner
from backend.services.solution_planner import SolutionPlannerError, _validate_learning_map
from backend.main import app


class SessionModeTests(unittest.IsolatedAsyncioTestCase):
    def test_concept_status_advances_only_with_distinct_quoted_student_evidence(self):
        concepts = ["Newton's second law", "Acceleration"]
        state = {}
        first = _validate_concept_updates(
            [ConceptUpdate(
                concept="NEWTONS SECOND LAW",
                status="mastered",
                evidence="same force, a heavier cart has less acceleration",
            )],
            concepts,
            "For the same force, a heavier cart has less acceleration.",
            state,
        )

        self.assertEqual(first[0].concept, "Newton's second law")
        self.assertEqual(first[0].status, "developing")
        self.assertEqual(state["newton's_second_law"]["evidence_count"], 1)

        repeated_quote = _validate_concept_updates(
            [ConceptUpdate(
                concept="Newton's second law",
                status="mastered",
                evidence="same force, a heavier cart has less acceleration",
            )],
            concepts,
            "For the same force, a heavier cart has less acceleration.",
            state,
        )
        self.assertEqual(repeated_quote, [])
        self.assertEqual(state["newton's_second_law"]["status"], "developing")

        second = _validate_concept_updates(
            [ConceptUpdate(
                concept="Newton's second law",
                status="mastered",
                evidence="heavier cart accelerates less",
            )],
            concepts,
            "The heavier cart accelerates less because its mass is greater.",
            state,
        )
        self.assertEqual(second[0].status, "mastered")
        self.assertEqual(state["newton's_second_law"]["score"], 1)

    def test_concept_updates_reject_unplanned_or_unquoted_evidence(self):
        state = {}
        updates = _validate_concept_updates(
            [
                ConceptUpdate(concept="Unplanned trivia", status="developing", evidence="I used inverse operations"),
                ConceptUpdate(concept="Inverse operations", status="developing", evidence="Tutor explained it"),
            ],
            ["Inverse operations"],
            "I subtracted seven from each side.",
            state,
        )

        self.assertEqual(updates, [])
        self.assertEqual(state, {})

    def test_needs_practice_requires_quote_and_resets_mastery_evidence(self):
        state = {"inverse_operations": {
            "id": "inverse_operations",
            "name": "Inverse operations",
            "status": "developing",
            "score": 0.5,
            "evidence_count": 1,
            "evidence_quotes": ["subtract seven from both sides"],
        }}
        updates = _validate_concept_updates(
            [ConceptUpdate(
                concept="Inverse operations",
                status="needs_practice",
                evidence="I added seven to both sides",
            )],
            ["Inverse operations"],
            "I added seven to both sides.",
            state,
        )

        self.assertEqual(updates[0].status, "needs_practice")
        self.assertEqual(state["inverse_operations"]["evidence_count"], 0)
        self.assertEqual(state["inverse_operations"]["score"], 0)

    async def test_solution_planner_builds_map_from_exact_question_without_replacing_concepts(self):
        problem_text = "Why does a heavier cart accelerate less when the same force is applied?"
        expected_map = {
            "key_steps": ["Connect force and mass to acceleration."],
            "common_misconceptions": [],
            "verifier": "none",
            "learning_objective": "Explain how mass changes acceleration under a constant force.",
            "concepts": ["Net force", "Mass and inertia", "Acceleration"],
            "concept_links": [
                {"source": "Net force", "target": "Mass and inertia"},
                {"source": "Mass and inertia", "target": "Acceleration"},
            ],
        }
        completion = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(expected_map)))]
        )
        create_completion = AsyncMock(return_value=completion)
        client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create_completion))
        )

        with patch.object(solution_planner, "_get_client", return_value=client):
            plan = await solution_planner.generate_solution_plan(
                problem_text,
                "conceptual",
                ["Friction"],
                "physics",
                "dynamics",
            )

        self.assertEqual(plan.concepts, expected_map["concepts"])
        self.assertEqual(plan.learning_objective, expected_map["learning_objective"])
        prompt = create_completion.await_args.kwargs["messages"][1]["content"]
        self.assertIn(problem_text, prompt)
        self.assertIn("Socratic scaffold", prompt)
        self.assertIn("Topic hint (may be generic; prioritize the exact question): dynamics", prompt)
        self.assertIn("do not blindly copy them into the map", prompt)

    def test_learning_map_rejects_cyclic_prerequisites(self):
        plan = SolutionPlan(
            key_steps=[],
            common_misconceptions=[],
            verifier="none",
            learning_objective="Understand the question-specific relationship.",
            concepts=["Concept A", "Concept B"],
            concept_links=[
                ConceptLink(source="Concept A", target="Concept B"),
                ConceptLink(source="Concept B", target="Concept A"),
            ],
        )

        with self.assertRaisesRegex(ValueError, "prerequisite cycle"):
            _validate_learning_map(plan)

    def test_planner_quota_error_is_actionable(self):
        self.assertIn("quota is exhausted", str(SolutionPlannerError(429)))

    async def test_session_creation_surfaces_map_planner_quota_failure(self):
        request = SessionCreate(problem_text="Explain why the sky appears blue.")

        async def fail_planning(*args, **kwargs):
            raise SolutionPlannerError(429)

        with (
            patch.object(sessions, "ensure_configured"),
            patch.object(sessions, "generate_solution_plan", side_effect=fail_planning),
            patch.object(sessions, "persist_session") as persist_session,
        ):
            with self.assertRaises(HTTPException) as error:
                await create_session(request, {"id": "user", "email": "student@example.com"})

        self.assertEqual(error.exception.status_code, 503)
        self.assertIn("quota is exhausted", error.exception.detail)
        persist_session.assert_not_called()

    def test_session_accepts_any_question_without_classification_metadata(self):
        session = SessionCreate(problem_text="What is the difference between weather and climate?")

        self.assertEqual(session.problem_type, "conceptual")
        self.assertEqual(session.subject, "general")
        self.assertEqual(session.topic, "open question")
        self.assertEqual(session.difficulty, "medium")
        self.assertEqual(session.language, "en")
        self.assertEqual(session.confidence_score, 0.3)
        self.assertEqual(session.concepts, [])

    async def test_session_creation_generates_and_returns_query_specific_learning_map(self):
        problem_text = "Why does increasing the mass of a cart reduce its acceleration under the same force?"
        request = SessionCreate(problem_text=problem_text, problem_type="conceptual")
        plan = SolutionPlan(
            key_steps=["Relate force, mass, and acceleration."],
            common_misconceptions=["Mass increases acceleration."],
            verifier="none",
            learning_objective="Explain how mass affects acceleration when force stays constant.",
            concepts=["Newton's second law", "Force-mass relationship", "Acceleration"],
            concept_links=[
                ConceptLink(source="Newton's second law", target="Force-mass relationship"),
                ConceptLink(source="Force-mass relationship", target="Acceleration"),
            ],
        )
        persisted = {}

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        def persist(*args, **kwargs):
            persisted["args"] = args
            persisted["kwargs"] = kwargs
            return {"id": "session-id"}

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "ensure_configured"),
            patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "curious_friend"}),
            patch.object(sessions, "persist_session", side_effect=persist),
            patch.object(sessions, "generate_solution_plan", new_callable=AsyncMock, return_value=plan) as plan_problem,
        ):
            result = await create_session(request, {"id": "user", "email": "student@example.com"})

        self.assertEqual(result["session_id"], "session-id")
        saved_plan = persisted["args"][9]
        self.assertEqual(saved_plan["verifier"], "none")
        self.assertEqual(persisted["kwargs"]["tutor_personality"], "curious_friend")
        self.assertEqual(saved_plan["concepts"], plan.concepts)
        self.assertEqual(result["learning_objective"], plan.learning_objective)
        self.assertEqual(result["concepts"][0]["name"], "Newton's second law")
        self.assertEqual(result["concept_links"][0], {
            "source": "newton's_second_law",
            "target": "force-mass_relationship",
        })
        plan_problem.assert_awaited_once_with(problem_text, "conceptual", [], "general", "open question")

    def test_http_session_start_returns_generated_learning_map(self):
        session_id = "00000000-0000-0000-0000-000000000123"
        plan = SolutionPlan(
            key_steps=["Identify the requested physical relationship."],
            common_misconceptions=[],
            verifier="none",
            learning_objective="Explain the relationship asked about in the question.",
            concepts=["Relevant principle", "Question-specific application"],
            concept_links=[ConceptLink(source="Relevant principle", target="Question-specific application")],
        )
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "test-user",
            "email": "student@example.com",
        }
        try:
            with (
                patch.object(sessions, "ensure_configured"),
                patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "chill_senior"}),
                patch.object(sessions, "persist_session", return_value={"id": session_id}),
                patch.object(sessions, "generate_solution_plan", new_callable=AsyncMock, return_value=plan) as planner,
            ):
                response = TestClient(app).post(
                    "/api/sessions",
                    headers={"Origin": "http://localhost:5173"},
                    json={"problem_text": "Why does increasing mass reduce acceleration?", "problem_type": "conceptual"},
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.headers.get("access-control-allow-origin"), "http://localhost:5173")
        self.assertEqual(response.json()["session_id"], session_id)
        self.assertEqual(response.json()["learning_objective"], plan.learning_objective)
        self.assertEqual(len(response.json()["concept_links"]), 1)
        planner.assert_awaited_once()

    async def test_restoring_session_returns_the_saved_learning_map_and_mastery(self):
        session_id = "00000000-0000-0000-0000-000000000123"
        session = {
            "id": session_id,
            "learning_state": {"concepts": {
                "newton's_second_law": {
                    "id": "newton's_second_law",
                    "name": "Newton's second law",
                    "status": "developing",
                    "score": 0.2,
                }
            }},
        }
        plan = {
            "learning_objective": "Explain how mass affects acceleration.",
            "concepts": ["Newton's second law", "Acceleration"],
            "concept_links": [{"source": "Newton's second law", "target": "Acceleration"}],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "chill_senior"}),
            patch.object(sessions, "list_messages", return_value=[]),
            patch.object(sessions, "get_session_rewards", return_value=0),
        ):
            result = await get_session(UUID(session_id), {"id": "user", "email": "student@example.com"})

        self.assertEqual(result["learning_objective"], plan["learning_objective"])
        self.assertEqual(result["concept_links"], [{
            "source": "newton's_second_law",
            "target": "acceleration",
        }])
        self.assertEqual(result["concepts"][0]["status"], "developing")

    def test_http_message_returns_actionable_error_when_provider_quota_is_exhausted(self):
        session_id = "00000000-0000-0000-0000-000000000124"
        app.dependency_overrides[get_current_user] = lambda: {
            "id": "test-user",
            "email": "student@example.com",
        }
        try:
            with (
                patch.object(
                    sessions,
                    "read_session",
                    return_value={
                        "id": session_id,
                        "status": "active",
                        "mode": "explore",
                        "problem_text": "Who is the current President of India?",
                        "problem_type": "conceptual",
                        "subject": "general",
                        "topic": "open question",
                        "learning_state": {},
                    },
                ),
                patch.object(
                    sessions,
                    "get_session_plan",
                    return_value={
                        "verifier": "none",
                        "final_answer": None,
                        "key_steps": [],
                        "common_misconceptions": [],
                        "concepts": [],
                        "transfer_problem": None,
                    },
                ),
                patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "chill_senior"}),
                patch.object(sessions, "list_messages", return_value=[]),
                patch.object(sessions, "add_message"),
                patch.object(
                    sessions,
                    "generate_tutor_response",
                    side_effect=TutorProviderError(429),
                ),
            ):
                response = TestClient(app).post(
                    f"/api/sessions/{session_id}/messages",
                    json={
                        "message": "Who is the current President of India?",
                        "mode": "explore",
                        "hint_level": 0,
                    },
                )
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        self.assertEqual(response.status_code, 503)
        self.assertIn("quota is exhausted", response.json()["detail"])

    async def test_message_route_passes_selected_mode_to_tutor(self):
        tutor_response = TutorResponse(
            response_type="question",
            message="What would you try first?",
            hint_level=0,
            concept_updates=[],
            mastery_evidence=[],
            verifier_status=None,
        )
        request = MessageRequest(message="I am not sure", mode="exam practice")
        session = {
            "id": "session-id",
            "problem_text": "What is 3x + 7 = 22?",
            "topic": "linear equations",
            "problem_type": "closed_form",
            "status": "active",
            "learning_state": {
                "misconceptions": [{
                    "conceptId": "linear-equations",
                    "description": "Combines unlike terms.",
                    "count": 1,
                }]
            },
        }
        plan = {
            "final_answer": None,
            "key_steps": [],
            "common_misconceptions": [],
            "verifier": "none",
            "concepts": [],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "curious_friend"}),
            patch.object(sessions, "list_messages", return_value=[
                {"role": "user", "content": "I subtracted 7 first.", "hint_level": 0},
                {"role": "tutor", "content": "What operation undoes multiplication?", "hint_level": 1},
            ]),
            patch.object(sessions, "set_session_mode") as save_mode,
            patch.object(sessions, "set_learning_state"),
            patch.object(sessions, "add_message"),
            patch.object(sessions, "generate_tutor_response", return_value=tutor_response) as generate_response,
            patch.object(sessions, "guard_answer", return_value={"leaks": False, "reason": ""}),
        ):
            result = await send_message("00000000-0000-0000-0000-000000000001", request, {"id": "user", "email": "student@example.com"})

        self.assertEqual(result, tutor_response)
        self.assertEqual(generate_response.call_args.args[3], "exam practice")
        self.assertEqual(generate_response.call_args.args[12], "curious_friend")
        self.assertEqual(
            generate_response.call_args.args[4],
            session["learning_state"]["misconceptions"],
        )
        self.assertEqual(
            generate_response.call_args.args[9],
            [
                {"role": "user", "content": "I subtracted 7 first.", "hint_level": 0},
                {"role": "tutor", "content": "What operation undoes multiplication?", "hint_level": 1},
            ],
        )
        self.assertEqual(generate_response.call_args.args[10], "linear equations")
        save_mode.assert_called_once_with(
            "00000000-0000-0000-0000-000000000001",
            "user",
            "exam practice",
        )

    async def test_message_route_skips_redundant_session_mode_write(self):
        tutor_response = TutorResponse(
            response_type="question",
            message="Which detail from the prompt seems important?",
            hint_level=0,
            concept_updates=[],
            mastery_evidence=[],
        )
        session_id = "00000000-0000-0000-0000-000000000001"
        session = {
            "id": session_id,
            "problem_text": "Explain photosynthesis.",
            "topic": "biology",
            "problem_type": "conceptual",
            "status": "active",
            "mode": "explore",
            "learning_state": {},
        }
        plan = {
            "final_answer": None,
            "key_steps": [],
            "common_misconceptions": [],
            "verifier": "none",
            "concepts": [],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "chill_senior"}),
            patch.object(sessions, "list_messages", return_value=[]),
            patch.object(sessions, "set_session_mode") as save_mode,
            patch.object(sessions, "set_learning_state"),
            patch.object(sessions, "add_message"),
            patch.object(sessions, "generate_tutor_response", return_value=tutor_response),
            patch.object(sessions, "guard_answer", return_value={"leaks": False, "reason": ""}),
        ):
            await send_message(
                session_id,
                MessageRequest(message="How does it work?", mode="explore"),
                {"id": "user", "email": "student@example.com"},
            )

        save_mode.assert_not_called()

    async def test_mastering_all_map_concepts_completes_learning_goal_without_reward(self):
        session_id = "00000000-0000-0000-0000-000000000001"
        request = MessageRequest(
            message="Acceleration is how much velocity changes each second.",
            mode="explore",
        )
        tutor_response = TutorResponse(
            response_type="question",
            message="What does that tell you about the cart?",
            hint_level=0,
            concept_updates=[
                ConceptUpdate(
                    concept="Acceleration",
                    status="mastered",
                    evidence="velocity changes each second",
                )
            ],
            mastery_evidence=[],
        )
        session = {
            "id": session_id,
            "problem_text": "Why does a heavier cart accelerate less?",
            "problem_type": "conceptual",
            "subject": "physics",
            "topic": "dynamics",
            "mode": "explore",
            "status": "active",
            "learning_state": {"concepts": {
                "newton's_second_law": {
                    "id": "newton's_second_law",
                    "name": "Newton's second law",
                    "status": "mastered",
                    "score": 1,
                    "evidence_count": 2,
                    "evidence_quotes": ["two separate force examples"],
                },
                "acceleration": {
                    "id": "acceleration",
                    "name": "Acceleration",
                    "status": "developing",
                    "score": 0.5,
                    "evidence_count": 1,
                    "evidence_quotes": ["change in velocity over time"],
                },
            }},
        }
        plan = {
            "final_answer": None,
            "key_steps": [],
            "common_misconceptions": [],
            "verifier": "none",
            "learning_objective": "Explain how mass changes acceleration under a constant force.",
            "concepts": ["Newton's second law", "Acceleration"],
            "concept_links": [{"source": "Newton's second law", "target": "Acceleration"}],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        saved_learning_state = {}
        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "chill_senior"}),
            patch.object(sessions, "list_messages", return_value=[]),
            patch.object(sessions, "add_message"),
            patch.object(sessions, "generate_tutor_response", return_value=tutor_response),
            patch.object(sessions, "guard_answer", return_value={"leaks": False, "reason": ""}),
            patch.object(sessions, "set_learning_state", side_effect=lambda _id, _user, state: saved_learning_state.update(state)),
            patch.object(sessions, "persist_completion") as persist_completion,
        ):
            result = await send_message(
                UUID(session_id),
                request,
                {"id": "user", "email": "student@example.com"},
            )

        self.assertTrue(result.session_completed)
        self.assertFalse(result.verified)
        self.assertEqual(result.response_type, "completion")
        self.assertEqual(result.reward_points, 0)
        self.assertEqual(saved_learning_state["concepts"]["acceleration"]["status"], "mastered")
        persist_completion.assert_called_once_with(session_id, "user", "learning_goal")

    def test_exam_practice_prompt_uses_exam_practice_strategy(self):
        prompt = build_prompt("closed_form", "mathematics", 0, "exam practice")

        self.assertIn("STUDENT MODE: exam practice", prompt)
        self.assertIn("encourage independent retrieval", prompt)

    async def test_factual_question_reaches_socratic_tutor(self):
        session_id = "00000000-0000-0000-0000-000000000001"
        tutor_response = TutorResponse(
            response_type="hint",
            message="A Chief Minister leads the state government. Which responsibility best explains that role?",
            hint_level=1,
            concept_updates=[],
            mastery_evidence=[],
        )
        session = {
            "id": session_id,
            "problem_text": "Who is the Chief Minister of Kerala?",
            "subject": "general",
            "topic": "civics",
            "problem_type": "conceptual",
            "status": "active",
            "learning_state": {},
        }
        plan = {
            "final_answer": None,
            "key_steps": [],
            "common_misconceptions": [],
            "verifier": "none",
            "concepts": [],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "get_user_profile", return_value={"tutor_personality": "chill_senior"}),
            patch.object(sessions, "list_messages", return_value=[]),
            patch.object(sessions, "set_session_mode"),
            patch.object(sessions, "set_learning_state"),
            patch.object(sessions, "add_message") as save_message,
            patch.object(sessions, "generate_tutor_response", return_value=tutor_response) as generate_response,
            patch.object(sessions, "guard_answer", return_value={"leaks": False, "reason": ""}),
        ):
            result = await send_message(
                session_id,
                MessageRequest(message="who is he", mode="explore"),
                {"id": "user", "email": "student@example.com"},
            )

        self.assertEqual(generate_response.call_args.args[0], "Who is the Chief Minister of Kerala?")
        self.assertEqual(generate_response.call_args.args[1], "who is he")
        self.assertEqual(generate_response.call_args.args[10], "civics")
        self.assertIn("Chief Minister", result.message)
        self.assertEqual(save_message.call_args.args[2], result.message)

    async def test_verified_solution_completes_session_and_awards_points(self):
        session_id = "00000000-0000-0000-0000-000000000001"
        request = MessageRequest(message="x = 5", mode="homework")
        session = {
            "id": session_id,
            "problem_text": "3x + 7 = 22",
            "problem_type": "closed_form",
            "status": "active",
            "learning_state": {},
        }
        plan = {
            "final_answer": "x = 5",
            "key_steps": [],
            "common_misconceptions": [],
            "verifier": "sympy",
            "concepts": ["Linear equations"],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "list_messages", return_value=[]),
            patch.object(sessions, "set_session_mode"),
            patch.object(sessions, "add_message"),
            patch.object(sessions, "award_verified_solution", return_value=10) as award,
            patch.object(sessions, "persist_completion") as complete,
        ):
            result = await send_message(session_id, request, {"id": "user", "email": "student@example.com"})

        self.assertTrue(result.session_completed)
        self.assertTrue(result.verified)
        self.assertEqual(result.reward_points, 10)
        award.assert_called_once_with("user", session_id, 10, 0)
        complete.assert_called_once_with(session_id, "user", "independent_solve")

    async def test_assisted_verified_solution_never_records_an_independent_streak(self):
        session_id = "00000000-0000-0000-0000-000000000002"
        request = MessageRequest(message="x = 5", mode="homework", hint_level=1)
        session = {
            "id": session_id,
            "problem_text": "3x + 7 = 22",
            "problem_type": "closed_form",
            "status": "active",
            "learning_state": {},
        }
        plan = {
            "final_answer": "x = 5",
            "key_steps": [],
            "common_misconceptions": [],
            "verifier": "sympy",
            "concepts": ["Linear equations"],
        }

        async def direct_call(function, *args, **kwargs):
            return function(*args, **kwargs)

        with (
            patch.object(sessions, "run_in_threadpool", side_effect=direct_call),
            patch.object(sessions, "read_session", return_value=session),
            patch.object(sessions, "get_session_plan", return_value=plan),
            patch.object(sessions, "list_messages", return_value=[
                {"role": "tutor", "content": "Try undoing the addition first.", "hint_level": 1},
            ]),
            patch.object(sessions, "set_session_mode"),
            patch.object(sessions, "add_message"),
            patch.object(sessions, "award_verified_solution", return_value=5) as award,
            patch.object(sessions, "persist_completion") as complete,
        ):
            result = await send_message(session_id, request, {"id": "user", "email": "student@example.com"})

        self.assertTrue(result.session_completed)
        self.assertFalse(result.independent_solve)
        award.assert_called_once_with("user", session_id, 5, 1)
        complete.assert_called_once_with(session_id, "user", "assisted_solve")


if __name__ == "__main__":
    unittest.main()
