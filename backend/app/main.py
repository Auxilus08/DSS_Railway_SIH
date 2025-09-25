import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .db import get_engine
from sqlalchemy import text

API_PREFIX = "/api"

app = FastAPI(title="SIH Backend")

# CORS for local dev
origins = [
    os.getenv("FRONTEND_URL", "http://localhost:5173"),
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get(f"{API_PREFIX}/health")
def health():
    return {"status": "ok"}


@app.get(f"{API_PREFIX}/db-check")
def db_check():
    try:
        engine = get_engine()
        with engine.connect() as conn:
            version = conn.execute(text("SELECT version();")).scalar_one()
        return {"status": "ok", "version": version}
    except Exception as e:
        return {"status": "error", "error": str(e)}
