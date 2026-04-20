"""
seed.py — Populate the database with sample data for development and testing.

Run with: python -m src.seed  (from the submission/ directory)
Or:       python src/seed.py  (from the submission/ directory)

Creates:
  - 2 institutions
  - 1 programme_manager + 1 monitoring_officer
  - 4 trainers
  - 15 students
  - 3 batches (2 under institution 1, 1 under institution 2)
  - Trainer <-> Batch assignments
  - Student ↔ Batch enrollments
  - 8 sessions spread across the 3 batches
  - Attendance records with a mix of present/absent/late
"""

import sys
import os
import random

# Ensure the project root is in the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
load_dotenv()

from src.database import engine, Base, SessionLocal
from src.models import (
    Institution, User, UserRole, Batch, Session,
    Attendance, AttendanceStatus, batch_trainers, batch_students,
)
from src.auth import hash_password


def seed():
    """Main seed function — idempotent (drops and recreates all tables)."""

    print("[SEED] SkillBridge Seed Script")
    print("=" * 50)

    # Recreate all tables (drop existing data)
    print("  -> Dropping existing tables...")
    Base.metadata.drop_all(bind=engine)
    print("  -> Creating tables...")
    Base.metadata.create_all(bind=engine)

    db = SessionLocal()

    try:
        # ─── 1. Institutions ────────────────────────────────────────
        print("  -> Creating institutions...")
        inst1 = Institution(name="Institute of Tech")
        inst2 = Institution(name="Skills Academy")
        db.add_all([inst1, inst2])
        db.commit()
        db.refresh(inst1)
        db.refresh(inst2)
        print(f"    [OK] {inst1.name} (id={inst1.id})")
        print(f"    [OK] {inst2.name} (id={inst2.id})")

        # ─── 2. Programme Manager & Monitoring Officer ──────────────
        print("  -> Creating programme manager & monitoring officer...")
        hashed = hash_password("password123")

        pm = User(
            name="Programme Manager",
            email="pm@skillbridge.com",
            hashed_password=hashed,
            role=UserRole.programme_manager,
        )
        mo = User(
            name="Monitoring Officer",
            email="monitor@skillbridge.com",
            hashed_password=hashed,
            role=UserRole.monitoring_officer,
        )
        db.add_all([pm, mo])
        db.commit()
        print(f"    [OK] pm@skillbridge.com (programme_manager)")
        print(f"    [OK] monitor@skillbridge.com (monitoring_officer)")

        # ─── 3. Trainers ───────────────────────────────────────────
        print("  -> Creating trainers...")
        trainers = []
        for i in range(1, 5):
            t = User(
                name=f"Trainer {i}",
                email=f"trainer{i}@skillbridge.com",
                hashed_password=hashed,
                role=UserRole.trainer,
                institution_id=inst1.id if i <= 2 else inst2.id,
            )
            trainers.append(t)
            db.add(t)
        db.commit()
        for t in trainers:
            db.refresh(t)
            print(f"    [OK] {t.email} (trainer, id={t.id})")

        # ─── 4. Students ──────────────────────────────────────────
        print("  -> Creating students...")
        students = []
        for i in range(1, 16):
            s = User(
                name=f"Student {i}",
                email=f"student{i}@skillbridge.com",
                hashed_password=hashed,
                role=UserRole.student,
            )
            students.append(s)
            db.add(s)
        db.commit()
        for s in students:
            db.refresh(s)
        print(f"    [OK] Created 15 students (student1 -> student15)")

        # ─── 5. Batches ───────────────────────────────────────────
        print("  -> Creating batches...")
        batch1 = Batch(name="Web Development Cohort A", institution_id=inst1.id)
        batch2 = Batch(name="Data Science Cohort B", institution_id=inst1.id)
        batch3 = Batch(name="Cloud Engineering Cohort C", institution_id=inst2.id)
        db.add_all([batch1, batch2, batch3])
        db.commit()
        db.refresh(batch1)
        db.refresh(batch2)
        db.refresh(batch3)
        batches = [batch1, batch2, batch3]
        for b in batches:
            print(f"    [OK] {b.name} (id={b.id}, institution={b.institution_id})")

        # ─── 6. Assign Trainers to Batches ────────────────────────
        print("  -> Assigning trainers to batches...")
        trainer_assignments = [
            (batch1.id, trainers[0].id),  # Trainer 1 -> Batch 1
            (batch1.id, trainers[1].id),  # Trainer 2 -> Batch 1
            (batch2.id, trainers[1].id),  # Trainer 2 -> Batch 2
            (batch2.id, trainers[2].id),  # Trainer 3 -> Batch 2
            (batch3.id, trainers[2].id),  # Trainer 3 -> Batch 3
            (batch3.id, trainers[3].id),  # Trainer 4 -> Batch 3
        ]
        for bid, tid in trainer_assignments:
            db.execute(batch_trainers.insert().values(batch_id=bid, trainer_id=tid))
        db.commit()
        print(f"    [OK] {len(trainer_assignments)} trainer <-> batch assignments")

        # ─── 7. Enroll Students in Batches ────────────────────────
        print("  -> Enrolling students in batches...")
        # Spread 15 students across 3 batches (5 each, with some overlap)
        enrollments = []
        for i, s in enumerate(students[:6]):
            enrollments.append((batch1.id, s.id))
        for i, s in enumerate(students[4:10]):
            enrollments.append((batch2.id, s.id))
        for i, s in enumerate(students[8:15]):
            enrollments.append((batch3.id, s.id))

        for bid, sid in enrollments:
            # Avoid duplicates
            existing = db.execute(
                batch_students.select().where(
                    (batch_students.c.batch_id == bid)
                    & (batch_students.c.student_id == sid)
                )
            ).first()
            if not existing:
                db.execute(batch_students.insert().values(batch_id=bid, student_id=sid))
        db.commit()
        print(f"    [OK] Students enrolled across batches")

        # ─── 8. Sessions ─────────────────────────────────────────
        print("  -> Creating sessions...")
        sessions_data = [
            # Batch 1 — 3 sessions
            {"batch_id": batch1.id, "trainer_id": trainers[0].id,
             "title": "HTML & CSS Basics", "date": "2024-10-01",
             "start_time": "09:00", "end_time": "11:00"},
            {"batch_id": batch1.id, "trainer_id": trainers[0].id,
             "title": "JavaScript Fundamentals", "date": "2024-10-03",
             "start_time": "09:00", "end_time": "11:00"},
            {"batch_id": batch1.id, "trainer_id": trainers[1].id,
             "title": "React Introduction", "date": "2024-10-05",
             "start_time": "14:00", "end_time": "16:00"},
            # Batch 2 — 3 sessions
            {"batch_id": batch2.id, "trainer_id": trainers[1].id,
             "title": "Python for Data Science", "date": "2024-10-02",
             "start_time": "10:00", "end_time": "12:00"},
            {"batch_id": batch2.id, "trainer_id": trainers[2].id,
             "title": "Pandas & NumPy", "date": "2024-10-04",
             "start_time": "10:00", "end_time": "12:00"},
            {"batch_id": batch2.id, "trainer_id": trainers[2].id,
             "title": "Machine Learning Intro", "date": "2024-10-06",
             "start_time": "14:00", "end_time": "16:00"},
            # Batch 3 — 2 sessions
            {"batch_id": batch3.id, "trainer_id": trainers[2].id,
             "title": "AWS Cloud Basics", "date": "2024-10-01",
             "start_time": "09:00", "end_time": "11:00"},
            {"batch_id": batch3.id, "trainer_id": trainers[3].id,
             "title": "Docker & Kubernetes", "date": "2024-10-03",
             "start_time": "09:00", "end_time": "11:00"},
        ]

        created_sessions = []
        for sd in sessions_data:
            s = Session(**sd)
            db.add(s)
            created_sessions.append(s)
        db.commit()
        for s in created_sessions:
            db.refresh(s)
        print(f"    [OK] Created {len(created_sessions)} sessions")

        # ─── 9. Attendance Records ────────────────────────────────
        print("  -> Creating attendance records...")
        statuses = [AttendanceStatus.present, AttendanceStatus.absent, AttendanceStatus.late]
        status_weights = [0.6, 0.2, 0.2]  # 60% present, 20% absent, 20% late
        attendance_count = 0

        for session_obj in created_sessions:
            # Find students enrolled in this session's batch
            enrolled = db.execute(
                batch_students.select().where(
                    batch_students.c.batch_id == session_obj.batch_id
                )
            ).fetchall()

            for enrollment in enrolled:
                student_id = enrollment.student_id
                chosen_status = random.choices(statuses, weights=status_weights, k=1)[0]
                att = Attendance(
                    session_id=session_obj.id,
                    student_id=student_id,
                    status=chosen_status,
                )
                db.add(att)
                attendance_count += 1

        db.commit()
        print(f"    [OK] Created {attendance_count} attendance records")

        # ─── Done ─────────────────────────────────────────────────
        print()
        print("=" * 50)
        print("[DONE] Seeding complete!")
        print()
        print("Test accounts (all use password: password123):")
        print("  Programme Manager : pm@skillbridge.com")
        print("  Monitoring Officer: monitor@skillbridge.com")
        print("  Trainers          : trainer1..4@skillbridge.com")
        print("  Students          : student1..15@skillbridge.com")

    except Exception as e:
        db.rollback()
        print(f"\n[ERROR] Seeding failed: {e}")
        raise
    finally:
        db.close()


if __name__ == "__main__":
    seed()
