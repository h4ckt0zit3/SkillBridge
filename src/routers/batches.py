"""
routers/batches.py — Batch management endpoints (create, invite, join).
"""

import uuid
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import Batch, BatchInvite, User, batch_students, batch_trainers, Institution
from src.schemas import BatchCreateRequest, BatchOut, InviteCreateResponse, JoinBatchRequest
from src.dependencies import require_role

router = APIRouter(prefix="/batches", tags=["Batches"])


@router.post("", response_model=BatchOut, status_code=status.HTTP_201_CREATED)
def create_batch(
    body: BatchCreateRequest,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("trainer", "institution")),
):
    """
    Create a new batch.

    Allowed roles: trainer, institution.
    """
    # Validate institution exists
    institution = db.query(Institution).filter(Institution.id == body.institution_id).first()
    if not institution:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Institution with id {body.institution_id} not found.",
        )

    batch = Batch(name=body.name, institution_id=body.institution_id)
    db.add(batch)
    db.commit()
    db.refresh(batch)

    # If the creator is a trainer, automatically assign them to the batch
    if current_user["role"] == "trainer":
        db.execute(
            batch_trainers.insert().values(
                batch_id=batch.id, trainer_id=current_user["user_id"]
            )
        )
        db.commit()

    return batch


@router.post("/{batch_id}/invite", response_model=InviteCreateResponse, status_code=status.HTTP_201_CREATED)
def create_invite(
    batch_id: int,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("trainer")),
):
    """
    Generate a unique invite token for students to join a batch.

    - Only trainers can create invites.
    - Token expires in 48 hours.
    """
    # Validate batch exists
    batch = db.query(Batch).filter(Batch.id == batch_id).first()
    if not batch:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Batch with id {batch_id} not found.",
        )

    # Generate unique token
    token = uuid.uuid4().hex
    expires_at = datetime.now(timezone.utc) + timedelta(hours=48)

    invite = BatchInvite(
        batch_id=batch_id,
        token=token,
        created_by=current_user["user_id"],
        expires_at=expires_at,
    )
    db.add(invite)
    db.commit()
    db.refresh(invite)

    return InviteCreateResponse(token=token, batch_id=batch_id, expires_at=expires_at)


@router.post("/join", status_code=status.HTTP_200_OK)
def join_batch(
    body: JoinBatchRequest,
    db: DBSession = Depends(get_db),
    current_user: dict = Depends(require_role("student")),
):
    """
    Student joins a batch using an invite token.

    Validates:
    - Token exists.
    - Token is not expired.
    - Token has not already been used.
    """
    invite = db.query(BatchInvite).filter(BatchInvite.token == body.token).first()
    if not invite:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid invite token.",
        )

    if invite.used:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite token has already been used.",
        )

    now = datetime.now(timezone.utc)
    # Handle both timezone-aware and naive datetimes from the DB
    expires = invite.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if now > expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This invite token has expired.",
        )

    # Enroll student in the batch
    student_id = current_user["user_id"]

    # Check if already enrolled
    existing = db.execute(
        batch_students.select().where(
            (batch_students.c.batch_id == invite.batch_id)
            & (batch_students.c.student_id == student_id)
        )
    ).first()

    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="You are already enrolled in this batch.",
        )

    db.execute(
        batch_students.insert().values(batch_id=invite.batch_id, student_id=student_id)
    )

    # Mark invite as used
    invite.used = True
    db.commit()

    return {"message": "Successfully joined the batch.", "batch_id": invite.batch_id}
