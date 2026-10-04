import logging
import re
from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field

from backend.models.schemas import ConceptUpdate, SolutionPlan, TutorResponse
from backend.services.ai_tutor import (
    TutorConfigurationError,
    TutorProviderError,
    TutorResponseFormatError,
    generate_tutor_response,
)
from backend.services.answer_guard import guard_answer
from backend.services.authentication import get_current_user
from backend.services.solution_planner import generate_solution_plan
from backend.services.supabase_store import (
    SupabaseError,
    add_message,
    award_verified_solution,
    complete_session as persist_completion,
    create_session as persist_session,
    ensure_configured,
    get_session as read_session,
    get_session_plan,
    list_messages,
    get_user_profile,
    set_session_mode,
    get_session_rewards,
    set_learning_state,
)
from backend.services.verifiers.sympy_verifier import verify_student_solution

router = APIRouter()
logger = logging.getLogger(__name__)

ProblemType = Literal["closed_form", "proof_derivation", "conceptual", "open_ended", "code", "mcq"]
TutorMode = Literal["homework", "exam practice", "explore"]


class SessionCreate(BaseModel):
    problem_text: str = Field(min_length=1, max_length=8000)
    problem_type: ProblemType = "conceptual"
    subject: str = Field(default="general", min_length=1, max_length=100)
    topic: str = Field(default="open question", min_length=1, max_length=200)
    difficulty: str = Field(default="medium", min_length=1, max_length=40)
    language: str = Field(default="en", min_length=2, max_length=20)
    confidence_score: float = Field(default=0.3, ge=0, le=1)
    concepts: list[str] = Field(default_factory=list, max_length=30)
    mode: TutorMode = "explore"
    tutor_personality: Literal["chill_senior", "strict_coach", "curious_friend"] | None = None


class MessageRequest(BaseModel):
    message: str = Field(min_length=1, max_length=4000)
    hint_level: int = Field(default=0, ge=0, le=3)
    mode: TutorMode = "explore"


def _concept_id(name: str) -> str:
    return re.sub(r"\s+", "_", name.strip().lower())


def _learning_map(plan: dict, learning_state: dict | None = None) -> dict:
    concept_state = (learning_state or {}).get("concepts", {})
    concepts = [
        concept_state.get(_concept_id(name), {
            "id": _concept_id(name),
            "name": name,
            "status": "not_assessed",
            "score": 0,
        })
        for name in plan.get("concepts", [])
    ]
    concept_links = [
        {
            "source": _concept_id(link["source"]),
            "target": _concept_id(link["target"]),
        }
        for link in plan.get("concept_links", [])
        if isinstance(link, dict) and link.get("source") and link.get("target")
    ]
    return {
        "learning_objective": plan.get("learning_objective"),
        "concepts": concepts,
        "concept_links": concept_links,
    }


def _concept_key(name: str) -> str:
    return re.sub(r"[\W_]+", "", name.casefold(), flags=re.UNICODE)


def _evidence_quotes_student(evidence: str, student_message: str) -> bool:
    evidence_words = re.findall(r"\w+", evidence.casefold(), flags=re.UNICODE)
    student_words = re.findall(r"\w+", student_message.casefold(), flags=re.UNICODE)
    if not evidence_words:
        return False
    if len(evidence_words) == 1:
        return evidence.strip().casefold() == student_message.strip().casefold()
    window_size = len(evidence_words)
    return any(
        student_words[index:index + window_size] == evidence_words
        for index in range(len(student_words) - window_size + 1)
    )


def _validate_concept_updates(
    updates: list[ConceptUpdate],
    planned_concepts: list[str],
    student_message: str,
    concept_state: dict,
) -> list[ConceptUpdate]:
    planned_by_key = {_concept_key(name): name for name in planned_concepts}
    accepted: list[ConceptUpdate] = []
    seen: set[str] = set()

    for update in updates:
        concept_key = _concept_key(update.concept)
        canonical_name = planned_by_key.get(concept_key)
        if canonical_name is None or concept_key in seen:
            continue
        if update.status not in {"mastered", "developing", "needs_practice"}:
            continue
        if not _evidence_quotes_student(update.evidence, student_message):
            continue
        seen.add(concept_key)

        concept_id = _concept_id(canonical_name)
        previous = concept_state.get(concept_id, {})
        previous_status = previous.get("status", "not_assessed")
        evidence_count = max(0, int(previous.get("evidence_count", 0)))
        evidence_quotes = previous.get("evidence_quotes", [])
        if any(
            _concept_key(update.evidence) == _concept_key(previous_quote)
            for previous_quote in evidence_quotes
            if isinstance(previous_quote, str)
        ):
            continue

        if update.status == "needs_practice":
            next_status = "needs_practice"
            next_evidence_count = 0
            next_evidence_quotes = []
        else:
            next_evidence_count = evidence_count + 1
            next_evidence_quotes = [*evidence_quotes, update.evidence][-8:]
            if previous_status == "mastered":
                next_status = "mastered"
            elif update.status == "mastered" and evidence_count >= 1:
                next_status = "mastered"
            else:
                next_status = "developing"

        accepted.append(update.model_copy(update={
            "concept": canonical_name,
            "status": next_status,
        }))
        concept_state[concept_id] = {
            "id": concept_id,
            "name": canonical_name,
            "status": next_status,
            "score": 0 if next_status == "needs_practice" else min(1, next_evidence_count / 2),
            "evidence_count": next_evidence_count,
            "evidence_quotes": next_evidence_quotes,
            "evidence": update.evidence[:500],
        }

    return accepted


@router.post("")
async def create_session(req: SessionCreate, user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(ensure_configured)
        plan = await generate_solution_plan(
            req.problem_text,
            req.problem_type,
            req.concepts,
            req.subject,
            req.topic,
        )
        personality = req.tutor_personality
        if personality is None:
            profile = await run_in_threadpool(get_user_profile, user["id"])
            personality = profile.get("tutor_personality") or "chill_senior"
        session = await run_in_threadpool(
            persist_session,
            user["id"],
            user["email"],
            req.problem_text,
            req.subject,
            req.topic,
            req.difficulty,
            req.language,
            req.problem_type,
            req.mode,
            plan.model_dump(),
            req.confidence_score,
            tutor_personality=personality,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="The tutor could not prepare this problem safely.") from exc
    except SupabaseError as exc:
        logger.exception("Session creation failed during Supabase persistence.")
        raise HTTPException(
            status_code=503,
            detail=f"Session storage is unavailable: {exc}",
        ) from exc
    return {
        "session_id": session["id"],
        "status": "created",
        "transfer_problem": plan.transfer_problem,
        **_learning_map(plan.model_dump()),
    }


@router.get("")
async def list_my_sessions(user: dict = Depends(get_current_user)):
    from backend.services.supabase_store import list_sessions

    try:
        sessions = await run_in_threadpool(list_sessions, user["id"])
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Session history is unavailable.") from exc
    return {"sessions": sessions}


@router.get("/{session_id}")
async def get_session(session_id: UUID, user: dict = Depends(get_current_user)):
    try:
        session = await run_in_threadpool(read_session, user["id"], str(session_id))
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        plan = await run_in_threadpool(get_session_plan, str(session_id))
        messages = await run_in_threadpool(list_messages, str(session_id))
        reward_points = await run_in_threadpool(get_session_rewards, user["id"], str(session_id))
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Session storage is unavailable.") from exc

    learning_map = _learning_map(plan or {}, session.get("learning_state"))
    return {
        "session": session,
        **learning_map,
        "misconceptions": (session.get("learning_state") or {}).get("misconceptions", []),
        "messages": messages,
        "reward_points": reward_points,
        "transfer_problem": (plan or {}).get("transfer_problem"),
    }


@router.post("/{session_id}/transfer")
async def start_transfer_problem(session_id: UUID, user: dict = Depends(get_current_user)):
    session_key = str(session_id)
    try:
        source_session = await run_in_threadpool(read_session, user["id"], session_key)
        if source_session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        source_plan = await run_in_threadpool(get_session_plan, session_key)
        transfer_problem = (source_plan or {}).get("transfer_problem")
        if not transfer_problem:
            raise HTTPException(status_code=409, detail="No transfer problem is available for this session.")

        await run_in_threadpool(ensure_configured)
        plan = await generate_solution_plan(
            transfer_problem,
            source_session.get("problem_type") or "closed_form",
            (source_plan or {}).get("concepts", []),
            source_session.get("subject"),
            source_session.get("topic"),
        )
        new_session = await run_in_threadpool(
            persist_session,
            user["id"],
            user["email"],
            transfer_problem,
            source_session["subject"],
            source_session["topic"],
            "medium",
            "en",
            source_session.get("problem_type") or "closed_form",
            "explore",
            plan.model_dump(),
            0.8,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="The transfer problem could not be prepared safely.") from exc
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Session storage is unavailable.") from exc

    return {
        "session_id": new_session["id"],
        "problem_text": transfer_problem,
        "problem_type": source_session.get("problem_type") or "closed_form",
        **_learning_map(plan.model_dump()),
        "mode": "explore",
        "transfer_problem": plan.transfer_problem,
    }


@router.post("/{session_id}/messages", response_model=TutorResponse)
async def send_message(
    session_id: UUID,
    req: MessageRequest,
    user: dict = Depends(get_current_user),
):
    session_key = str(session_id)
    try:
        session = await run_in_threadpool(read_session, user["id"], session_key)
        if session is None:
            raise HTTPException(status_code=404, detail="Session not found.")
        if session.get("status") == "completed":
            raise HTTPException(status_code=409, detail="This session is already complete.")
        plan_data = await run_in_threadpool(get_session_plan, session_key)
        if not plan_data:
            raise HTTPException(status_code=409, detail="This session is missing its private assessment plan.")

        previous_messages = await run_in_threadpool(list_messages, session_key)
        learning_state = session.get("learning_state") or {}
        prior_hint_count = sum(
            1
            for message in previous_messages
            if message["role"] == "tutor" and message.get("hint_level", 0) > 0
        )
        if session.get("mode") != req.mode:
            await run_in_threadpool(set_session_mode, session_key, user["id"], req.mode)
        await run_in_threadpool(
            add_message,
            session_key,
            "user",
            req.message,
            req.hint_level,
        )
    except SupabaseError as exc:
        logger.exception("Tutor message request failed during Supabase persistence.")
        raise HTTPException(
            status_code=503,
            detail=f"Session storage is unavailable: {exc}",
        ) from exc

    plan = SolutionPlan(**plan_data)
    if plan.verifier == "sympy" and await run_in_threadpool(
        verify_student_solution,
        session["problem_text"],
        req.message,
        plan.final_answer,
    ):
        points = 10 if prior_hint_count == 0 else 5
        try:
            awarded = await run_in_threadpool(
                award_verified_solution,
                user["id"],
                session_key,
                points,
                prior_hint_count,
            )
            is_independent = prior_hint_count == 0 and req.hint_level == 0
            await run_in_threadpool(
                persist_completion,
                session_key,
                user["id"],
                "independent_solve" if is_independent else "assisted_solve",
            )
            completed_response = TutorResponse(
                response_type="completion",
                message="Your result checks out. Nice work—explain the key idea you used, or try another problem.",
                hint_level=min(req.hint_level, 3),
                concept_updates=[],
                mastery_evidence=["The submitted value satisfies the problem equation."],
                verifier_status="verified",
                session_completed=True,
                verified=True,
                independent_solve=is_independent,
                reward_points=awarded,
            )
            await run_in_threadpool(
                add_message,
                session_key,
                "tutor",
                completed_response.message,
                completed_response.hint_level,
            )
        except SupabaseError as exc:
            raise HTTPException(status_code=503, detail="Verified progress could not be saved. Please retry.") from exc
        return completed_response

    try:
        profile = await run_in_threadpool(get_user_profile, user["id"])
        response = await run_in_threadpool(
            generate_tutor_response,
            session["problem_text"],
            req.message,
            req.hint_level,
            req.mode,
            learning_state.get("misconceptions", []),
            plan_data.get("concepts", []),
            session.get("problem_type") or "closed_form",
            plan_data,
            session.get("subject") or "general",
            previous_messages[-12:],
            session.get("topic") or "unclear",
            [
                {
                    "name": name,
                    **learning_state.get("concepts", {}).get(_concept_id(name), {
                        "status": "not_assessed",
                        "evidence_count": 0,
                    }),
                }
                for name in plan_data.get("concepts", [])
            ],
            profile.get("tutor_personality") or session.get("tutor_personality") or "chill_senior",
        )
    except TutorProviderError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TutorConfigurationError as exc:
        logger.error("Tutor response generation is unavailable: AI configuration is missing.")
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except TutorResponseFormatError as exc:
        logger.warning("Tutor response validation failed (%s).", type(exc.__cause__).__name__)
        raise HTTPException(
            status_code=502,
            detail="The AI tutor returned an invalid response. Please retry.",
        ) from exc
    except RuntimeError as exc:
        logger.error("Unexpected tutor response generation failure: %s.", str(exc))
        raise HTTPException(status_code=502, detail="The tutor could not create a response. Please retry.") from exc

    if guard_answer(response.message, plan)["leaks"]:
        logger.warning("Tutor response was rejected by the answer-safety check.")
        raise HTTPException(
            status_code=502,
            detail="The tutor response could not pass its answer-safety check. Please retry.",
        )

    concept_state = learning_state.get("concepts", {})
    misconception_state = learning_state.get("misconceptions", [])
    response.concept_updates = _validate_concept_updates(
        response.concept_updates,
        plan.concepts,
        req.message,
        concept_state,
    )
    for update in response.concept_updates:
        concept_id = _concept_id(update.concept)
        if update.status == "needs_practice":
            prior = next(
                (
                    item for item in misconception_state
                    if item["conceptId"] == concept_id and item["description"] == update.evidence[:500]
                ),
                None,
            )
            if prior:
                prior["count"] = min(99, prior.get("count", 1) + 1)
            elif len(misconception_state) < 50:
                misconception_state.append({
                    "id": f"{concept_id}-{len(misconception_state)}",
                    "conceptId": concept_id,
                    "description": update.evidence[:500] or "Review this concept.",
                    "count": 1,
                })
    learning_state["concepts"] = concept_state
    learning_state["misconceptions"] = misconception_state
    try:
        await run_in_threadpool(set_learning_state, session_key, user["id"], learning_state)
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Learning progress could not be saved. Please retry.") from exc

    objective_mastered = bool(plan.concepts) and all(
        concept_state.get(_concept_id(name), {}).get("status") == "mastered"
        for name in plan.concepts
    )
    if objective_mastered:
        try:
            await run_in_threadpool(persist_completion, session_key, user["id"], "learning_goal")
        except SupabaseError as exc:
            raise HTTPException(status_code=503, detail="Completed learning progress could not be saved. Please retry.") from exc
        response.response_type = "completion"
        response.message = (
            "You demonstrated the key ideas in your learning map. Nice work—"
            "review your progress or start a new problem whenever you're ready."
        )
        response.session_completed = True
        response.verified = False
        response.reward_points = 0
    else:
        response.session_completed = False
        response.verified = False
        response.reward_points = 0
    if response.response_type == "completion" and not objective_mastered:
        response.response_type = "verification"
        response.message = "Before we call this complete, try one more step that shows how you know your reasoning holds."
    if response.response_type == "hint":
        response.hint_level = max(1, response.hint_level)

    try:
        stored_hint_level = max(1, response.hint_level) if response.response_type == "hint" else 0
        response.hint_level = stored_hint_level
        await run_in_threadpool(
            add_message,
            session_key,
            "tutor",
            response.message,
            stored_hint_level,
        )
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="The tutor reply could not be saved. Please retry.") from exc
    return response
