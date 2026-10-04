import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

from backend.config import APP_NAME
from backend.api import account, problems, rewards, sessions

app = FastAPI(title=f"{APP_NAME} API")
allowed_origins = [
    origin.strip()
    for origin in os.environ.get(
        "API_ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173",
    ).split(",")
    if origin.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(problems.router, prefix="/api/problems", tags=["Problems"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Sessions"])
app.include_router(rewards.router, prefix="/api/rewards", tags=["Rewards"])
app.include_router(account.router, prefix="/api/account", tags=["Account"])

@app.get("/")
def health_check():
    return {"status": "ok"}
