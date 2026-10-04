from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool

from backend.services.authentication import get_current_user
from backend.services.supabase_store import SupabaseError, get_reward_balance


router = APIRouter()


@router.get("/balance")
async def reward_balance(user: dict = Depends(get_current_user)):
    try:
        points = await run_in_threadpool(get_reward_balance, user["id"])
    except SupabaseError as exc:
        raise HTTPException(status_code=503, detail="Reward history is unavailable.") from exc
    return {"points": points}
