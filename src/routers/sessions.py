"""
routers/sessions.py — Session management and programme-level summary endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import Session, Batch, Institution, batch_trainers
from src.schemas import (
    SessionCreateRequest, SessionOut,
    InstitutionSummaryOut, ProgrammeSummaryOut,
    BatchSummaryOut, AttendanceSummarySession,
)
from src.dependencies import require_role

router = APIRouter(tags=["Sessions"])


# ─── Session Creation ────────────────────────────────────────────────────────

@router.post("/sessions", response_model=SessionOut, status_code=status.HTTP_201_CREATED)
def create_session(
    body: SessionCreateRequest,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("trainer")),
):
    """
    Create a new training session.

    Validations:
    - Batch must exist (404).
    - Trainer must be assigned to the batch (403).
    """
    # Validate batch exists
    batch = db.query(Batch).filter(Batch.id == body.batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with id {body.batch_id} not found.",
        )

    # Validate trainer belongs to the batch
    trainer_id = current_user["user_id"]
    membership = db.execute(
        batch_trainers.select().where(
            (batch_trainers.c.batch_id == body.batch_id)
            & (batch_trainers.c.trainer_id == trainer_id)
        )
    ).first()

    if not membership:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this batch.",
        )

    session = Session(
        batch_id=body.batch_id,
        trainer_id=trainer_id,
        title=body.title,
        date=body.date,
        start_time=body.start_time,
        end_time=body.end_time,
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


# ─── Programme-Level Summaries ───────────────────────────────────────────────

def _build_batch_summary(batch: Batch) -> BatchSummaryOut:
    """Helper to build attendance summary for a single batch."""
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


@router.get(
    "/institutions/{institution_id}/summary",
    response_model=InstitutionSummaryOut,
)
def institution_summary(
    institution_id: int,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("programme_manager")),
):
    """
    Return attendance summary across all batches in an institution.

    Allowed role: programme_manager.
    """
    institution = db.query(Institution).filter(Institution.id == institution_id).first()
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with id {institution_id} not found.",
        )

    batches_summary = [_build_batch_summary(b) for b in institution.batches]

    return InstitutionSummaryOut(
        institution_id=institution.id,
        institution_name=institution.name,
        batches=batches_summary,
    )


@router.get("/programme/summary", response_model=ProgrammeSummaryOut)
def programme_summary(
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("programme_manager")),
):
    """
    Return programme-wide summary across ALL institutions.

    Allowed role: programme_manager.
    """
    institutions = db.query(Institution).all()
    result = []
    for inst in institutions:
        batches_summary = [_build_batch_summary(b) for b in inst.batches]
        result.append(
            InstitutionSummaryOut(
                institution_id=inst.id,
                institution_name=inst.name,
                batches=batches_summary,
            )
        )

    return ProgrammeSummaryOut(institutions=result)
