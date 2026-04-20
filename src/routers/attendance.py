"""
routers/attendance.py — Attendance marking and reporting endpoints.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import (
    Attendance, AttendanceStatus, Session, Batch,
    batch_students,
)
from src.schemas import (
    AttendanceMarkRequest, AttendanceOut,
    BatchSummaryOut, AttendanceSummarySession,
)
from src.dependencies import require_role

router = APIRouter(tags=["Attendance"])


# ─── Mark Attendance ─────────────────────────────────────────────────────────

@router.post("/attendance/mark", response_model=AttendanceOut, status_code=status.HTTP_200_OK)
def mark_attendance(
    body: AttendanceMarkRequest,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("student")),
):
    """
    Student marks their attendance for a session.

    Validations:
    - Session must exist (404).
    - Student must be enrolled in the batch that the session belongs to (403).
    - Status must be one of: present, absent, late (422).
    """
    # Validate attendance status
    valid_statuses = [s.value for s in AttendanceStatus]
    if body.status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid status '{body.status}'. Must be one of: {', '.join(valid_statuses)}",
        )

    # Validate session exists
    session = db.query(Session).filter(Session.id == body.session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {body.session_id} not found.",
        )

    # Validate student is enrolled in the session's batch
    student_id = current_user["user_id"]
    enrollment = db.execute(
        batch_students.select().where(
            (batch_students.c.batch_id == session.batch_id)
            & (batch_students.c.student_id == student_id)
        )
    ).first()

    if not enrollment:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not enrolled in the batch for this session.",
        )

    # Create the attendance record
    record = Attendance(
        session_id=body.session_id,
        student_id=student_id,
        status=AttendanceStatus(body.status),
    )
    db.add(record)
    db.commit()
    db.refresh(record)

    return record


# ─── Session Attendance List (trainer) ───────────────────────────────────────

@router.get(
    "/sessions/{session_id}/attendance",
    response_model=List[AttendanceOut],
)
def get_session_attendance(
    session_id: int,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("trainer")),
):
    """
    Return all attendance records for a given session.

    Allowed role: trainer.
    """
    session = db.query(Session).filter(Session.id == session_id).first()
    if not session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Session with id {session_id} not found.",
        )

    records = db.query(Attendance).filter(Attendance.session_id == session_id).all()
    return records


# ─── Batch Attendance Summary (institution) ──────────────────────────────────

@router.get(
    "/batches/{batch_id}/summary",
    response_model=BatchSummaryOut,
)
def get_batch_summary(
    batch_id: int,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("institution")),
):
    """
    Return attendance summary for all sessions in a batch.

    Allowed role: institution.
    """
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with id {batch_id} not found.",
        )

    session_summaries = []
    for s in batch.sessions:
        records = s.attendance_records
        total = len(records)
        present = sum(1 for r in records if r.status.value == "present")
        absent = sum(1 for r in records if r.status.value == "absent")
        late = sum(1 for r in records if r.status.value == "late")
        session_summaries.append(
            AttendanceSummarySession(
                session_id=s.id,
                title=s.title,
                date=s.date,
                total_students=total,
                present=present,
                absent=absent,
                late=late,
            )
        )

    return BatchSummaryOut(
        batch_id=batch.id,
        batch_name=batch.name,
        sessions=session_summaries,
    )
