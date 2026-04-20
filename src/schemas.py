"""
schemas.py — Pydantic v2 schemas for request/response validation.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, EmailStr, Field


# ─── Auth Schemas ─────────────────────────────────────────────────────────────

class SignupRequest(BaseModel):
    """Request body for POST /auth/signup."""
    name: str = Field(..., min_length=1, description="Full name of the user")
    email: EmailStr = Field(..., description="User email address")
    password: str = Field(..., min_length=6, description="Password (min 6 chars)")
    role: str = Field(..., description="One of: student, trainer, institution, programme_manager, monitoring_officer")


class LoginRequest(BaseModel):
    """Request body for POST /auth/login."""
    email: EmailStr
    password: str


class MonitoringTokenRequest(BaseModel):
    """Request body for POST /auth/monitoring-token."""
    key: str = Field(..., description="API key for monitoring access")


class TokenResponse(BaseModel):
    """Response containing a JWT access token."""
    access_token: str
    token_type: str = "bearer"


# ─── Institution Schemas ─────────────────────────────────────────────────────

class InstitutionOut(BaseModel):
    id: int
    name: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── User Schemas ────────────────────────────────────────────────────────────

class UserOut(BaseModel):
    id: int
    name: str
    email: str
    role: str
    institution_id: Optional[int] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Batch Schemas ───────────────────────────────────────────────────────────

class BatchCreateRequest(BaseModel):
    """Request body for POST /batches."""
    name: str = Field(..., min_length=1)
    institution_id: int


class BatchOut(BaseModel):
    id: int
    name: str
    institution_id: int
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class InviteCreateResponse(BaseModel):
    """Response after generating a batch invite."""
    token: str
    batch_id: int
    expires_at: datetime


class JoinBatchRequest(BaseModel):
    """Request body for POST /batches/join."""
    token: str


# ─── Session Schemas ─────────────────────────────────────────────────────────

class SessionCreateRequest(BaseModel):
    """Request body for POST /sessions."""
    title: str = Field(..., min_length=1)
    date: str = Field(..., description="ISO date YYYY-MM-DD")
    start_time: str = Field(..., description="HH:MM")
    end_time: str = Field(..., description="HH:MM")
    batch_id: int


class SessionOut(BaseModel):
    id: int
    batch_id: int
    trainer_id: int
    title: str
    date: str
    start_time: str
    end_time: str
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─── Attendance Schemas ──────────────────────────────────────────────────────

class AttendanceMarkRequest(BaseModel):
    """Request body for POST /attendance/mark."""
    session_id: int
    status: str = Field(..., description="One of: present, absent, late")


class AttendanceOut(BaseModel):
    id: int
    session_id: int
    student_id: int
    status: str
    marked_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AttendanceSummarySession(BaseModel):
    """Attendance summary for a single session."""
    session_id: int
    title: str
    date: str
    total_students: int
    present: int
    absent: int
    late: int


class BatchSummaryOut(BaseModel):
    """Attendance summary for a batch."""
    batch_id: int
    batch_name: str
    sessions: List[AttendanceSummarySession]


class InstitutionSummaryOut(BaseModel):
    """Summary across all batches in an institution."""
    institution_id: int
    institution_name: str
    batches: List[BatchSummaryOut]


class ProgrammeSummaryOut(BaseModel):
    """Programme-wide summary across all institutions."""
    institutions: List[InstitutionSummaryOut]


# ─── Monitoring Schemas ─────────────────────────────────────────────────────

class MonitoringAttendanceOut(BaseModel):
    """Single attendance record for the monitoring endpoint."""
    id: int
    session_id: int
    student_id: int
    student_name: str
    status: str
    marked_at: Optional[datetime] = None
    batch_id: int
    batch_name: str
    session_title: str
    session_date: str
