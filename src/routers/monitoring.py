"""
routers/monitoring.py — Monitoring endpoints with dual-token authentication.

The GET /monitoring/attendance endpoint requires a special monitoring token
(token_type == "monitoring") rather than a standard JWT.

All non-GET methods return 405 Method Not Allowed.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import Attendance, Session, Batch, User
from src.schemas import MonitoringAttendanceOut
from src.auth import decode_token

router = APIRouter(prefix="/monitoring", tags=["Monitoring"])

bearer_scheme = HTTPBearer(auto_error=False)


def require_monitoring_token(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Custom dependency that validates the monitoring token.

    Unlike the standard get_current_user, this checks that
    token_type == "monitoring" in the JWT payload.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Monitoring token required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired monitoring token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("token_type") != "monitoring":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token type. A monitoring token is required.",
        )

    return payload


@router.get("/attendance", response_model=List[MonitoringAttendanceOut])
def get_monitoring_attendance(
    db: DBSession = Depends(get_db),
    token_payload: dict = Depends(require_monitoring_token),
):
    """
    Return all attendance records across the system.

    Requires a valid monitoring token (token_type == "monitoring").
    """
    records = (
        db.query(Attendance)
        .join(Session, Attendance.session_id == Session.id)
        .join(Batch, Session.batch_id == Batch.id)
        .join(User, Attendance.student_id == User.id)
        .all()
    )

    result = []
    for r in records:
        result.append(
            MonitoringAttendanceOut(
                id=r.id,
                session_id=r.session_id,
                student_id=r.student_id,
                student_name=r.student.name,
                status=r.status.value,
                marked_at=r.marked_at,
                batch_id=r.session.batch_id,
                batch_name=r.session.batch.name,
                session_title=r.session.title,
                session_date=r.session.date,
            )
        )
    return result


# ─── 405 for all non-GET methods ────────────────────────────────────────────

@router.post("/attendance")
@router.put("/attendance")
@router.patch("/attendance")
@router.delete("/attendance")
def monitoring_attendance_method_not_allowed():
    """All non-GET methods on /monitoring/attendance return 405."""
    raise HTTPException(
        status_code=status.HTTP_405_METHOD_NOT_ALLOWED,
        detail="Only GET is allowed on /monitoring/attendance.",
    )
