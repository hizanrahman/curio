from datetime import datetime, timezone
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, ConfigDict, Field

from backend.services.authentication import get_current_user
from backend.services.supabase_store import (
    SupabaseError,
    delete_account,
    get_user_profile,
    save_user,
    update_user_profile,
)


router = APIRouter()


class AccountDeletionRequest(BaseModel):
    confirm_email: str = Field(min_length=3, max_length=320)


class ProfileUpdateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tutor_personality: Literal["chill_senior", "strict_coach", "curious_friend"] | None = None


@router.get("/profile")
async def get_my_profile(user: dict = Depends(get_current_user)):
    try:
        await run_in_threadpool(save_user, user["id"], user["email"])
        profile = await run_in_threadpool(get_user_profile, user["id"])
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Your profile is temporarily unavailable.") from exc
    return {
        "tutor_personality": profile.get("tutor_personality") or "chill_senior",
    }


@router.patch("/profile")
async def update_my_profile(
    request: ProfileUpdateRequest,
    user: dict = Depends(get_current_user),
):
    fields = request.model_dump(exclude_unset=True)
    if not fields:
        raise HTTPException(status_code=422, detail="Provide at least one profile setting to update.")
    try:
        profile = await run_in_threadpool(update_user_profile, user["id"], user["email"], fields)
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Your profile could not be saved.") from exc
    return {
        "tutor_personality": profile.get("tutor_personality") or "chill_senior",
    }


@router.delete("")
async def delete_my_account(
    request: AccountDeletionRequest,
    user: dict = Depends(get_current_user),
):
    if request.confirm_email.casefold() != user["email"].casefold():
        raise HTTPException(status_code=400, detail="Enter the email address on your account to confirm deletion.")
    auth_time = user.get("auth_time")
    if auth_time is None or datetime.now(timezone.utc).timestamp() - auth_time > 300:
        raise HTTPException(status_code=401, detail="Sign in again immediately before deleting your account.")
    try:
        await run_in_threadpool(delete_account, user["id"])
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Account data could not be deleted. Please retry.") from exc
    return {"status": "deleted"}
