"""
main.py — FastAPI application entry point for SkillBridge.

Includes all routers and creates database tables on startup.
Run with: uvicorn src.main:app --reload
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI

from src.database import engine, Base
from src.routers import auth, batches, sessions, attendance, monitoring

# Import models so SQLAlchemy sees them before create_all
import src.models  # noqa: F401


# ─── Lifespan: auto-create all tables on startup ────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Create all database tables on startup."""
    Base.metadata.create_all(bind=engine)
    yield


# ─── Create FastAPI App ─────────────────────────────────────────────────────

app = FastAPI(
    title="SkillBridge API",
    description=(
        "Attendance management REST API with role-based access control, "
        "JWT authentication, batch management, session tracking, and "
        "programme-level monitoring."
    ),
    version="1.0.0",
    lifespan=lifespan,
)


# ─── Include Routers ────────────────────────────────────────────────────────

app.include_router(auth.router)          # /auth/*
app.include_router(batches.router)       # /batches/*
app.include_router(sessions.router)      # /sessions/*, /institutions/*, /programme/*
app.include_router(attendance.router)    # /attendance/*, /sessions/*/attendance, /batches/*/summary
app.include_router(monitoring.router)    # /monitoring/*


# ─── Root Health Check ──────────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Root endpoint — health check."""
    return {
        "service": "SkillBridge API",
        "status": "running",
        "version": "1.0.0",
    }
