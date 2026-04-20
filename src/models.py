"""
models.py — SQLAlchemy ORM models for the SkillBridge attendance system.

Tables:
  institutions, users, batches, batch_trainers, batch_students,
  batch_invites, sessions, attendance
"""

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, ForeignKey, Enum, Table
)
from sqlalchemy.orm import relationship

from src.database import Base


# ─── Enums ────────────────────────────────────────────────────────────────────

class UserRole(str, enum.Enum):
    """Allowed user roles."""
    student = "student"
    trainer = "trainer"
    institution = "institution"
    programme_manager = "programme_manager"
    monitoring_officer = "monitoring_officer"


class AttendanceStatus(str, enum.Enum):
    """Allowed attendance statuses."""
    present = "present"
    absent = "absent"
    late = "late"


# ─── Association Tables (many-to-many) ───────────────────────────────────────

batch_trainers = Table(
    "batch_trainers",
    Base.metadata,
    Column("batch_id", Integer, ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True),
    Column("trainer_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)

batch_students = Table(
    "batch_students",
    Base.metadata,
    Column("batch_id", Integer, ForeignKey("batches.id", ondelete="CASCADE"), primary_key=True),
    Column("student_id", Integer, ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),
)


# ─── ORM Models ──────────────────────────────────────────────────────────────

class Institution(Base):
    """An educational institution."""
    __tablename__ = "institutions"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    users = relationship("User", back_populates="institution")
    batches = relationship("Batch", back_populates="institution")


class User(Base):
    """A user of the system (student, trainer, institution admin, etc.)."""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    institution = relationship("Institution", back_populates="users")

    # Many-to-many via association tables
    trained_batches = relationship("Batch", secondary=batch_trainers, back_populates="trainers")
    enrolled_batches = relationship("Batch", secondary=batch_students, back_populates="students")


class Batch(Base):
    """A training batch belonging to an institution."""
    __tablename__ = "batches"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    institution_id = Column(Integer, ForeignKey("institutions.id"), nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    institution = relationship("Institution", back_populates="batches")
    trainers = relationship("User", secondary=batch_trainers, back_populates="trained_batches")
    students = relationship("User", secondary=batch_students, back_populates="enrolled_batches")
    sessions = relationship("Session", back_populates="batch")
    invites = relationship("BatchInvite", back_populates="batch")


class BatchInvite(Base):
    """A token-based invite for students to join a batch."""
    __tablename__ = "batch_invites"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    token = Column(String, unique=True, nullable=False, index=True)
    created_by = Column(Integer, ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    used = Column(Boolean, default=False)

    # Relationships
    batch = relationship("Batch", back_populates="invites")
    creator = relationship("User")


class Session(Base):
    """A training session within a batch."""
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True, index=True)
    batch_id = Column(Integer, ForeignKey("batches.id", ondelete="CASCADE"), nullable=False)
    trainer_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String, nullable=False)
    date = Column(String, nullable=False)          # ISO date string (YYYY-MM-DD)
    start_time = Column(String, nullable=False)     # HH:MM
    end_time = Column(String, nullable=False)       # HH:MM
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    batch = relationship("Batch", back_populates="sessions")
    trainer = relationship("User")
    attendance_records = relationship("Attendance", back_populates="session")


class Attendance(Base):
    """An attendance record for a student in a session."""
    __tablename__ = "attendance"

    id = Column(Integer, primary_key=True, index=True)
    session_id = Column(Integer, ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    status = Column(Enum(AttendanceStatus), nullable=False)
    marked_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))

    # Relationships
    session = relationship("Session", back_populates="attendance_records")
    student = relationship("User")
