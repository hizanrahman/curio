import base64
import binascii
import json
import logging
import os
import ssl
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request

from fastapi import Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.services.supabase_transport import urlopen

bearer_scheme = HTTPBearer(auto_error=False)
logger = logging.getLogger(__name__)
TLS_HANDSHAKE_RETRIES = 2
AUTH_NETWORK_RETRIES = 2
AUTH_REQUEST_TIMEOUT_SECONDS = 15


def _verify_token(token: str, base_url: str, anon_key: str) -> dict:
    request = Request(
        f"{base_url}/auth/v1/user",
        headers={
            "apikey": anon_key,
            "Authorization": f"Bearer {token}",
        },
    )
    for attempt in range(max(TLS_HANDSHAKE_RETRIES, AUTH_NETWORK_RETRIES) + 1):
        try:
            with urlopen(request, timeout=AUTH_REQUEST_TIMEOUT_SECONDS) as response:
                user = json.loads(response.read())
            break
        except HTTPError as exc:
            if exc.code in (400, 401, 403):
                exc.close()
                raise HTTPException(status_code=401, detail="Your sign-in has expired. Please sign in again.") from exc
            try:
                error_payload = json.loads(exc.read())
                error_code = error_payload.get("code") if isinstance(error_payload, dict) else None
            except (json.JSONDecodeError, OSError):
                error_code = None
            finally:
                exc.close()
            logger.warning(
                "Supabase sign-in verification returned HTTP %s (error code %s).",
                exc.code,
                error_code if isinstance(error_code, str) else "unavailable",
            )
            detail = f"Supabase sign-in verification returned HTTP {exc.code}."
            if isinstance(error_code, str):
                detail = f"Supabase sign-in verification returned HTTP {exc.code} (code {error_code})."
            raise HTTPException(status_code=502, detail=detail) from exc
        except URLError as exc:
            if isinstance(exc.reason, ssl.SSLError) and attempt < TLS_HANDSHAKE_RETRIES:
                logger.warning(
                    "Retrying Supabase sign-in verification after TLS handshake failure (%s/%s).",
                    attempt + 1,
                    TLS_HANDSHAKE_RETRIES,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            if isinstance(exc.reason, TimeoutError) and attempt < AUTH_NETWORK_RETRIES:
                logger.warning(
                    "Retrying Supabase sign-in verification after request timeout (%s/%s).",
                    attempt + 1,
                    AUTH_NETWORK_RETRIES,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            if isinstance(exc.reason, ssl.SSLError):
                raise HTTPException(
                    status_code=502,
                    detail="Supabase sign-in verification failed during TLS handshake after retries.",
                ) from exc
            reason = exc.reason
            if isinstance(reason, TimeoutError):
                detail = "Supabase sign-in verification timed out."
            else:
                detail = (
                    "Supabase sign-in verification could not connect "
                    f"({type(reason).__name__})."
                )
            logger.warning("Supabase sign-in verification network failure: %s.", type(reason).__name__)
            raise HTTPException(status_code=502, detail=detail) from exc
        except ssl.SSLError as exc:
            if attempt < TLS_HANDSHAKE_RETRIES:
                logger.warning(
                    "Retrying Supabase sign-in verification after TLS response failure (%s/%s).",
                    attempt + 1,
                    TLS_HANDSHAKE_RETRIES,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            logger.warning("Supabase sign-in verification TLS failure after retries.")
            raise HTTPException(
                status_code=502,
                detail="Supabase sign-in verification failed during TLS communication after retries.",
            ) from exc
        except (TimeoutError, OSError) as exc:
            if isinstance(exc, TimeoutError) and attempt < AUTH_NETWORK_RETRIES:
                logger.warning(
                    "Retrying Supabase sign-in verification after response timeout (%s/%s).",
                    attempt + 1,
                    AUTH_NETWORK_RETRIES,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            if not isinstance(exc, TimeoutError) and attempt < TLS_HANDSHAKE_RETRIES:
                logger.warning(
                    "Retrying Supabase sign-in verification after connection failure (%s, %s/%s).",
                    type(exc).__name__,
                    attempt + 1,
                    TLS_HANDSHAKE_RETRIES,
                )
                time.sleep(0.2 * (2 ** attempt))
                continue
            if isinstance(exc, TimeoutError):
                detail = "Supabase sign-in verification timed out after retries."
            else:
                detail = (
                    "Supabase sign-in verification could not complete after retries "
                    f"({type(exc).__name__})."
                )
            logger.warning("Supabase sign-in verification failed: %s.", type(exc).__name__)
            raise HTTPException(status_code=502, detail=detail) from exc
        except json.JSONDecodeError as exc:
            raise HTTPException(status_code=502, detail="Supabase returned an invalid sign-in response.") from exc

    if not isinstance(user, dict) or not user.get("id") or not user.get("email"):
        raise HTTPException(status_code=401, detail="A verified email account is required.")
    if not user.get("email_confirmed_at") and not user.get("confirmed_at"):
        raise HTTPException(status_code=403, detail="Confirm your email address before using saved learning sessions.")

    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        claims = json.loads(base64.urlsafe_b64decode(payload))
        if claims.get("sub") != user["id"]:
            raise ValueError("Token subject mismatch.")
        password_auth_times = [
            int(method["timestamp"])
            for method in claims.get("amr", [])
            if method.get("method") == "password" and method.get("timestamp") is not None
        ]
        auth_time = max(password_auth_times) if password_auth_times else None
    except (IndexError, KeyError, TypeError, ValueError, AttributeError, binascii.Error, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=401, detail="Your sign-in token is invalid.") from exc

    return {"id": user["id"], "email": user["email"], "auth_time": auth_time}


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    if credentials is None:
        raise HTTPException(status_code=401, detail="Sign in to continue.")
    base_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", os.environ.get("SUPABASE_KEY", ""))
    if not base_url or not anon_key:
        raise HTTPException(status_code=503, detail="Authentication is not configured.")
    parsed_url = urlparse(base_url)
    if parsed_url.scheme != "https" and parsed_url.hostname not in {"localhost", "127.0.0.1"}:
        raise HTTPException(status_code=503, detail="Supabase must use HTTPS outside local development.")

    return await run_in_threadpool(
        _verify_token,
        credentials.credentials,
        base_url,
        anon_key,
    )
