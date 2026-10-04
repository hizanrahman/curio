import json
import logging
import os
import ssl
import time
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlparse
from urllib.request import Request
from uuid import uuid4

from backend.services.supabase_transport import urlopen

logger = logging.getLogger(__name__)
TLS_HANDSHAKE_RETRIES = 2
IDEMPOTENT_NETWORK_RETRIES = 2


class SupabaseError(Exception):
    pass


def ensure_configured() -> None:
    _settings()


def _settings() -> tuple[str, str]:
    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    service_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")
    if not base_url or not service_key:
        raise SupabaseError("Supabase persistence is not configured.")
    parsed_url = urlparse(base_url)
    if parsed_url.scheme != "https" and parsed_url.hostname not in {"localhost", "127.0.0.1"}:
        raise SupabaseError("Supabase must use HTTPS outside local development.")
    return base_url, service_key


def _request(
    path: str,
    method: str = "GET",
    body: dict | None = None,
    prefer: str | None = None,
    retryable_post: bool = False,
) -> object:
    base_url, service_key = _settings()
    resource = path.split("?", 1)[0].split("/", 1)[0]
    headers = {
        "apikey": service_key,
        "Authorization": f"Bearer {service_key}",
        "Content-Type": "application/json",
    }
    if prefer:
        headers["Prefer"] = prefer
    data = json.dumps(body).encode("utf-8") if body is not None else None
    request = Request(f"{base_url}/rest/v1/{path}", data=data, headers=headers, method=method)
    retries = TLS_HANDSHAKE_RETRIES
    if method in {"GET", "PATCH", "DELETE"} or (method == "POST" and retryable_post):
        retries = max(retries, IDEMPOTENT_NETWORK_RETRIES)
    retryable_method = method in {"GET", "PATCH", "DELETE"} or (method == "POST" and retryable_post)
    for attempt in range(retries + 1):
        try:
            with urlopen(request, timeout=15) as response:
                payload = response.read()
            break
        except HTTPError as exc:
            if retryable_method and exc.code in {502, 503, 504} and attempt < retries:
                exc.close()
                logger.warning(
                    "Retrying Supabase %s on %s after HTTP %s (%s/%s).",
                    method,
                    resource,
                    exc.code,
                    attempt + 1,
                    retries,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            try:
                error_payload = json.loads(exc.read())
                error_code = error_payload.get("code") if isinstance(error_payload, dict) else None
            except (json.JSONDecodeError, OSError):
                error_code = None
            finally:
                exc.close()
            message = f"Supabase {method} on {resource} failed with HTTP {exc.code}"
            if isinstance(error_code, str):
                message += f" (database/API code {error_code})"
            raise SupabaseError(message + ".") from exc
        except URLError as exc:
            if isinstance(exc.reason, ssl.SSLError) and attempt < TLS_HANDSHAKE_RETRIES:
                logger.warning(
                    "Retrying Supabase %s on %s after a TLS handshake failure (%s/%s).",
                    method,
                    resource,
                    attempt + 1,
                    TLS_HANDSHAKE_RETRIES,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            if retryable_method and attempt < retries:
                logger.warning(
                    "Retrying Supabase %s on %s after network failure (%s, %s/%s).",
                    method,
                    resource,
                    type(exc.reason).__name__,
                    attempt + 1,
                    retries,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            if isinstance(exc.reason, ssl.SSLError):
                raise SupabaseError(
                    f"Supabase {method} on {resource} failed during TLS handshake after "
                    f"{attempt + 1} attempts."
                ) from exc
            reason_type = type(exc.reason).__name__
            raise SupabaseError(
                f"Supabase {method} on {resource} could not be reached after "
                f"{attempt + 1} attempt(s) ({reason_type})."
            ) from exc
        except ssl.SSLError as exc:
            if retryable_method and attempt < retries:
                logger.warning(
                    "Retrying Supabase %s on %s after TLS response failure (%s/%s).",
                    method,
                    resource,
                    attempt + 1,
                    retries,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            logger.warning("Supabase %s on %s failed during TLS communication.", method, resource)
            raise SupabaseError(
                f"Supabase {method} on {resource} failed during TLS communication."
            ) from exc
        except (TimeoutError, OSError) as exc:
            if retryable_method and attempt < retries:
                logger.warning(
                    "Retrying Supabase %s on %s after connection failure (%s, %s/%s).",
                    method,
                    resource,
                    type(exc).__name__,
                    attempt + 1,
                    retries,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            logger.warning("Supabase %s on %s failed: %s.", method, resource, type(exc).__name__)
            raise SupabaseError(
                f"Supabase {method} on {resource} could not complete "
                f"({type(exc).__name__})."
            ) from exc
    if not payload:
        return None
    try:
        return json.loads(payload)
    except json.JSONDecodeError as exc:
        raise SupabaseError("Supabase returned an invalid response.") from exc


def save_user(user_id: str, email: str) -> None:
    _request(
        "users?on_conflict=id",
        method="POST",
        body={"id": user_id, "email": email},
        prefer="resolution=merge-duplicates,return=minimal",
    )


def get_user_profile(user_id: str) -> dict:
    query = urlencode(
        {
            "select": "tutor_personality",
            "id": f"eq.{user_id}",
        }
    )
    result = _request(f"users?{query}")
    return result[0] if isinstance(result, list) and result else {}


def update_user_profile(user_id: str, email: str, profile: dict) -> dict:
    save_user(user_id, email)
    _request(
        f"users?{urlencode({'id': f'eq.{user_id}'})}",
        method="PATCH",
        body=profile,
        prefer="return=minimal",
    )
    return get_user_profile(user_id)


def create_session(
    user_id: str,
    email: str,
    problem_text: str,
    subject: str,
    topic: str,
    difficulty: str,
    language: str,
    problem_type: str,
    mode: str,
    solution_plan: dict,
    tutor_confidence: float,
    tutor_personality: str | None = None,
) -> dict:
    save_user(user_id, email)
    session_body = {
        "user_id": user_id,
        "problem_text": problem_text,
        "subject": subject,
        "topic": topic,
        "status": "active",
        "mode": mode,
        "problem_type": problem_type,
    }
    if tutor_personality:
        session_body["tutor_personality"] = tutor_personality
    created = _request(
        "sessions",
        method="POST",
        body=session_body,
        prefer="return=representation",
    )
    if not isinstance(created, list) or not created:
        raise SupabaseError("Supabase did not return the created session.")
    session = created[0]
    try:
        _request(
            "problems",
            method="POST",
            body={
                "session_id": session["id"],
                "problem_type": problem_type,
                "subject": subject,
                "topic": topic,
                "difficulty": difficulty,
                "language": language,
                "solution_plan": solution_plan,
                "tutor_confidence": tutor_confidence,
            },
            prefer="return=minimal",
        )
    except SupabaseError:
        session_id = quote(str(session["id"]), safe="")
        try:
            _request(f"sessions?id=eq.{session_id}&user_id=eq.{quote(user_id, safe='')}", method="DELETE")
        except SupabaseError:
            logger.exception("Failed to roll back a session after its private plan could not be saved.")
        raise
    return session


def get_session(user_id: str, session_id: str) -> dict | None:
    query = urlencode(
        {
            "select": "id,user_id,problem_text,subject,topic,status,started_at,completed_at,mode,problem_type,learning_state,completion_kind,tutor_personality",
            "id": f"eq.{session_id}",
            "user_id": f"eq.{user_id}",
        }
    )
    result = _request(f"sessions?{query}")
    return result[0] if isinstance(result, list) and result else None


def list_sessions(user_id: str) -> list[dict]:
    query = urlencode(
        {
            "select": "id,problem_text,subject,topic,status,started_at,completed_at,mode,problem_type",
            "user_id": f"eq.{user_id}",
            "order": "started_at.desc",
            "limit": "100",
        }
    )
    result = _request(f"sessions?{query}")
    return result if isinstance(result, list) else []


def get_session_plan(session_id: str) -> dict | None:
    query = urlencode({"select": "solution_plan", "session_id": f"eq.{session_id}"})
    result = _request(f"problems?{query}")
    return result[0].get("solution_plan") if isinstance(result, list) and result else None


def list_messages(session_id: str) -> list[dict]:
    query = urlencode(
        {
            "select": "id,role,content,hint_level,created_at",
            "session_id": f"eq.{session_id}",
            "order": "created_at.asc",
        }
    )
    result = _request(f"messages?{query}")
    return result if isinstance(result, list) else []


def add_message(session_id: str, role: str, content: str, hint_level: int = 0) -> dict:
    result = _request(
        "messages?on_conflict=id",
        method="POST",
        body={
            "id": str(uuid4()),
            "session_id": session_id,
            "role": role,
            "content": content,
            "hint_level": hint_level,
        },
        prefer="resolution=merge-duplicates,return=representation",
        retryable_post=True,
    )
    if not isinstance(result, list) or not result:
        raise SupabaseError("Supabase did not return the saved message.")
    return result[0]


def set_session_mode(session_id: str, user_id: str, mode: str) -> None:
    query = urlencode({"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"})
    _request(f"sessions?{query}", method="PATCH", body={"mode": mode}, prefer="return=minimal")


def set_learning_state(session_id: str, user_id: str, learning_state: dict) -> None:
    query = urlencode({"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"})
    _request(
        f"sessions?{query}",
        method="PATCH",
        body={"learning_state": learning_state},
        prefer="return=minimal",
    )


def complete_session(session_id: str, user_id: str, completion_kind: str | None = None) -> None:
    query = urlencode({"id": f"eq.{session_id}", "user_id": f"eq.{user_id}"})
    body = {"status": "completed", "completed_at": datetime.now(timezone.utc).isoformat()}
    if completion_kind:
        body["completion_kind"] = completion_kind
    _request(
        f"sessions?{query}",
        method="PATCH",
        body=body,
        prefer="return=minimal",
    )


def award_verified_solution(
    user_id: str,
    session_id: str,
    points: int,
    hint_count: int,
) -> int:
    query = urlencode({"on_conflict": "user_id,session_id,reason"})
    result = _request(
        f"reward_ledger?{query}",
        method="POST",
        body={
            "user_id": user_id,
            "session_id": session_id,
            "reason": "verified_problem_solved",
            "points": points,
            "evidence": {"verifier": "sympy", "prior_hint_count": hint_count},
        },
        prefer="resolution=ignore-duplicates,return=representation",
    )
    if isinstance(result, list) and result:
        return int(result[0]["points"])

    existing_query = urlencode(
        {
            "select": "points",
            "user_id": f"eq.{user_id}",
            "session_id": f"eq.{session_id}",
            "reason": "eq.verified_problem_solved",
        }
    )
    existing = _request(f"reward_ledger?{existing_query}")
    if isinstance(existing, list) and existing:
        return int(existing[0]["points"])
    raise SupabaseError("The reward could not be confirmed.")


def get_reward_balance(user_id: str) -> int:
    result = _request(
        f"reward_ledger?{urlencode({'select': 'points', 'user_id': f'eq.{user_id}'})}"
    )
    return sum(int(item["points"]) for item in result) if isinstance(result, list) else 0


def get_session_rewards(user_id: str, session_id: str) -> int:
    result = _request(
        "reward_ledger?"
        + urlencode(
            {
                "select": "points",
                "user_id": f"eq.{user_id}",
                "session_id": f"eq.{session_id}",
            }
        )
    )
    return sum(int(item["points"]) for item in result) if isinstance(result, list) else 0


def delete_account(user_id: str) -> None:
    base_url, service_key = _settings()
    _request(
        f"users?{urlencode({'id': f'eq.{user_id}'})}",
        method="DELETE",
    )
    request = Request(
        f"{base_url}/auth/v1/admin/users/{quote(user_id, safe='')}",
        headers={
            "apikey": service_key,
            "Authorization": f"Bearer {service_key}",
        },
        method="DELETE",
    )
    try:
        with urlopen(request, timeout=15):
            pass
    except HTTPError as exc:
        raise SupabaseError(f"Supabase account deletion failed with status {exc.code}.") from exc
    except URLError as exc:
        raise SupabaseError("Supabase could not be reached for account deletion.") from exc
