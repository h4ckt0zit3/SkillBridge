"""
test_api.py — Integration tests for the SkillBridge API.

These tests use httpx with a real test database. Ensure DATABASE_URL in .env
points to a test database before running.

Run with: pytest tests/test_api.py -v
"""

import sys
import os

# Ensure the project root is in the path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
from fastapi.testclient import TestClient

from src.main import app
from src.database import engine, Base, SessionLocal
from src.models import (
    User, UserRole, Batch, Session, Institution,
    batch_trainers, batch_students,
)
from src.auth import hash_password


# ─── Fixtures ────────────────────────────────────────────────────────────────

@pytest.fixture(scope="module", autouse=True)
def setup_database():
    """
    Create all tables before tests run and drop them after.
    This uses a real database — make sure DATABASE_URL points to a test DB.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)

    # Seed minimal data for tests that need existing records
    db = SessionLocal()
    try:
        hashed = hash_password("password123")

        # Institution
        inst = Institution(name="Test Institute")
        db.add(inst)
        db.commit()
        db.refresh(inst)

        # Trainer
        trainer = User(
            name="Test Trainer",
            email="testtrainer@test.com",
            hashed_password=hashed,
            role=UserRole.trainer,
            institution_id=inst.id,
        )
        db.add(trainer)
        db.commit()
        db.refresh(trainer)

        # Batch
        batch = Batch(name="Test Batch", institution_id=inst.id)
        db.add(batch)
        db.commit()
        db.refresh(batch)

        # Assign trainer to batch
        db.execute(
            batch_trainers.insert().values(batch_id=batch.id, trainer_id=trainer.id)
        )

        # Student (pre-enrolled for attendance test)
        student = User(
            name="Test Student",
            email="teststudent@test.com",
            hashed_password=hashed,
            role=UserRole.student,
        )
        db.add(student)
        db.commit()
        db.refresh(student)

        # Enroll student in batch
        db.execute(
            batch_students.insert().values(batch_id=batch.id, student_id=student.id)
        )

        # Session
        session = Session(
            batch_id=batch.id,
            trainer_id=trainer.id,
            title="Test Session",
            date="2024-10-01",
            start_time="09:00",
            end_time="11:00",
        )
        db.add(session)
        db.commit()
        db.refresh(session)

        db.commit()
    finally:
        db.close()

    yield

    Base.metadata.drop_all(bind=engine)


@pytest.fixture(scope="module")
def client():
    """HTTP test client that talks to the FastAPI app."""
    with TestClient(app) as c:
        yield c


# ─── Helper ─────────────────────────────────────────────────────────────────

def login(client: TestClient, email: str, password: str) -> str:
    """Login and return the access token."""
    resp = client.post("/auth/login", json={"email": email, "password": password})
    assert resp.status_code == 200, f"Login failed: {resp.text}"
    return resp.json()["access_token"]


# ─── Tests ───────────────────────────────────────────────────────────────────

def test_student_signup_and_login(client: TestClient):
    """
    Test 1: Sign up as a student and then log in.
    Asserts that a JWT is returned in both cases.
    """
    # Signup
    signup_resp = client.post("/auth/signup", json={
        "name": "New Student",
        "email": "newstudent@test.com",
        "password": "password123",
        "role": "student",
    })
    assert signup_resp.status_code == 201, f"Signup failed: {signup_resp.text}"
    data = signup_resp.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"

    # Login
    login_resp = client.post("/auth/login", json={
        "email": "newstudent@test.com",
        "password": "password123",
    })
    assert login_resp.status_code == 200, f"Login failed: {login_resp.text}"
    login_data = login_resp.json()
    assert "access_token" in login_data
    assert login_data["token_type"] == "bearer"


def test_trainer_create_session(client: TestClient):
    """
    Test 2: Log in as a trainer and create a session. Assert 201.
    """
    token = login(client, "testtrainer@test.com", "password123")

    # Get the batch ID (we know batch 1 exists from seed)
    db = SessionLocal()
    batch = db.query(Batch).first()
    db.close()

    resp = client.post(
        "/sessions",
        json={
            "title": "Integration Test Session",
            "date": "2024-11-01",
            "start_time": "10:00",
            "end_time": "12:00",
            "batch_id": batch.id,
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 201, f"Create session failed: {resp.text}"
    data = resp.json()
    assert data["title"] == "Integration Test Session"
    assert data["batch_id"] == batch.id


def test_student_mark_attendance(client: TestClient):
    """
    Test 3: Log in as a student (pre-enrolled) and mark attendance. Assert 200.
    """
    token = login(client, "teststudent@test.com", "password123")

    # Get the session ID from the seed data
    db = SessionLocal()
    session = db.query(Session).filter(Session.title == "Test Session").first()
    db.close()

    resp = client.post(
        "/attendance/mark",
        json={
            "session_id": session.id,
            "status": "present",
        },
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 200, f"Mark attendance failed: {resp.text}"
    data = resp.json()
    assert data["status"] == "present"
    assert data["session_id"] == session.id


def test_post_monitoring_returns_405(client: TestClient):
    """
    Test 4: POST to /monitoring/attendance must return 405 Method Not Allowed.
    """
    resp = client.post("/monitoring/attendance")
    assert resp.status_code == 405, (
        f"Expected 405 for POST /monitoring/attendance, got {resp.status_code}: {resp.text}"
    )


def test_protected_endpoint_no_token(client: TestClient):
    """
    Test 5: GET /monitoring/attendance with no token must return 401.
    """
    resp = client.get("/monitoring/attendance")
    assert resp.status_code == 401, (
        f"Expected 401 for unauthenticated GET /monitoring/attendance, "
        f"got {resp.status_code}: {resp.text}"
    )
