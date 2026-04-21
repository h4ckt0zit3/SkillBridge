# SkillBridge — Attendance Management REST API

> A production-ready REST API for managing attendance across training programmes, built with FastAPI, PostgreSQL, and JWT authentication.

---

## Table of Contents

1. [Features](#features)
2. [Tech Stack](#tech-stack)
3. [Local Setup](#local-setup)
4. [Test Accounts](#test-accounts)
5. [API Endpoints & Curl Examples](#api-endpoints--curl-examples)
6. [JWT Payload Structure](#jwt-payload-structure)
7. [Schema Design Decisions](#schema-design-decisions)
8. [Token Rotation & Revocation](#token-rotation--revocation)
9. [Security Considerations](#security-considerations)
10. [Project Status](#project-status)

---

## Features

- **5 user roles**: student, trainer, institution, programme_manager, monitoring_officer
- **JWT authentication** with role-based access control (RBAC)
- **Batch management** with invite-token-based student enrollment
- **Session & attendance tracking** with per-batch and programme-wide summaries
- **Dual-token monitoring** system with short-lived tokens
- **Auto-created tables** on startup (no migration tool needed)
- **Comprehensive seed script** for demo data
- **Integration tests** with pytest + httpx

---

## Tech Stack

| Layer | Technology |
|---|---|
| Framework | FastAPI |
| Database | PostgreSQL (via SQLAlchemy ORM) |
| Auth | JWT (python-jose) + bcrypt (passlib) |
| Validation | Pydantic v2 |
| Testing | pytest + httpx |
| Env management | python-dotenv |

---

## Local Setup

### Prerequisites

- Python 3.11+
- PostgreSQL database (local or remote)
- `pip` and `venv`

### Step-by-step

```bash
# 1. Clone the repo and navigate into it
cd submission/

# 2. Create and activate a virtual environment
python -m venv venv
# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.example .env
# Then edit .env with your values:
#   DATABASE_URL=postgresql://user:password@localhost:5432/skillbridge
#   SECRET_KEY=your-super-secret-key-here
#   ALGORITHM=HS256
#   ACCESS_TOKEN_EXPIRE_MINUTES=1440
#   MONITORING_API_KEY=skillbridge-monitor-key-2024

# 5. Seed the database with sample data
python src/seed.py

# 6. Start the dev server
uvicorn src.main:app --reload
```

The API will be available at `http://127.0.0.1:8000`. Interactive docs at `http://127.0.0.1:8000/docs`.

### Running Tests

```bash
pytest tests/test_api.py -v
```

> **Note:** Tests use the same `DATABASE_URL` from `.env`. Point it to a test database to avoid polluting production data.

---

## Test Accounts

All seeded accounts use password: **`password123`**

| Role | Email | Password |
|---|---|---|
| Programme Manager | `pm@skillbridge.com` | `password123` |
| Monitoring Officer | `monitor@skillbridge.com` | `password123` |
| Trainer 1 | `trainer1@skillbridge.com` | `password123` |
| Trainer 2 | `trainer2@skillbridge.com` | `password123` |
| Trainer 3 | `trainer3@skillbridge.com` | `password123` |
| Trainer 4 | `trainer4@skillbridge.com` | `password123` |
| Student 1–15 | `student1@skillbridge.com` ... `student15@skillbridge.com` | `password123` |

**Monitoring API Key:** `skillbridge-monitor-key-2024`

---

## API Endpoints & Curl Examples

Replace `BASE` with your actual URL (e.g., `http://127.0.0.1:8000` locally).

### Auth

#### Sign Up
```bash
curl -X POST $BASE/auth/signup \
  -H "Content-Type: application/json" \
  -d '{"name": "Jane Doe", "email": "jane@example.com", "password": "securepass123", "role": "student"}'
```

#### Log In
```bash
curl -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "trainer1@skillbridge.com", "password": "password123"}'
```
Response: `{"access_token": "<JWT>", "token_type": "bearer"}`

#### Get Monitoring Token
```bash
# First, login as monitoring officer to get a standard JWT
STANDARD_TOKEN=$(curl -s -X POST $BASE/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "monitor@skillbridge.com", "password": "password123"}' | jq -r '.access_token')

# Then exchange it + API key for a monitoring token
curl -X POST $BASE/auth/monitoring-token \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STANDARD_TOKEN" \
  -d '{"key": "skillbridge-monitor-key-2024"}'
```

### Batches

#### Create Batch (trainer or institution)
```bash
curl -X POST $BASE/batches \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TRAINER_TOKEN" \
  -d '{"name": "New Cohort D", "institution_id": 1}'
```

#### Generate Invite Token (trainer only)
```bash
curl -X POST $BASE/batches/1/invite \
  -H "Authorization: Bearer $TRAINER_TOKEN"
```

#### Join Batch (student only)
```bash
curl -X POST $BASE/batches/join \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -d '{"token": "<invite_token_from_above>"}'
```

### Sessions

#### Create Session (trainer only)
```bash
curl -X POST $BASE/sessions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TRAINER_TOKEN" \
  -d '{"title": "Advanced React", "date": "2024-10-10", "start_time": "09:00", "end_time": "11:00", "batch_id": 1}'
```

### Attendance

#### Mark Attendance (student only)
```bash
curl -X POST $BASE/attendance/mark \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $STUDENT_TOKEN" \
  -d '{"session_id": 1, "status": "present"}'
```

#### Get Session Attendance (trainer only)
```bash
curl -X GET $BASE/sessions/1/attendance \
  -H "Authorization: Bearer $TRAINER_TOKEN"
```

#### Get Batch Summary (institution only)
```bash
curl -X GET $BASE/batches/1/summary \
  -H "Authorization: Bearer $INSTITUTION_TOKEN"
```

### Programme

#### Institution Summary (programme_manager only)
```bash
curl -X GET $BASE/institutions/1/summary \
  -H "Authorization: Bearer $PM_TOKEN"
```

#### Programme-wide Summary (programme_manager only)
```bash
curl -X GET $BASE/programme/summary \
  -H "Authorization: Bearer $PM_TOKEN"
```

### Monitoring

#### Get All Attendance (monitoring token required)
```bash
curl -X GET $BASE/monitoring/attendance \
  -H "Authorization: Bearer $MONITORING_TOKEN"
```

#### POST Returns 405
```bash
curl -X POST $BASE/monitoring/attendance
# Response: 405 Method Not Allowed
```

---

## JWT Payload Structure

### Standard Token
```json
{
  "user_id": 1,
  "role": "trainer",
  "token_type": "standard",
  "iat": 1700000000,
  "exp": 1700086400
}
```
- **Expiry:** 24 hours (1440 minutes)
- **Issued on:** signup or login

### Monitoring Token
```json
{
  "user_id": 5,
  "role": "monitoring_officer",
  "token_type": "monitoring",
  "iat": 1700000000,
  "exp": 1700003600
}
```
- **Expiry:** 1 hour
- **Issued via:** `POST /auth/monitoring-token` with a valid API key + monitoring_officer JWT

---

## Schema Design Decisions

### `batch_trainers` (many-to-many)

A batch can have multiple trainers, and a trainer can be assigned to multiple batches. This is modeled as a join table with a composite primary key `(batch_id, trainer_id)` rather than embedding trainer IDs into the batch record, which supports flexible assignment and clean queries.

### `batch_invites` (token-based joining)

Instead of open enrollment, students join batches via invite tokens. Each invite:
- Is a unique UUID string
- Has a 48-hour expiry
- Can only be used once (`used` boolean flag)
- Tracks who created it (`created_by` FK)

This prevents unauthorized enrollment and provides an audit trail.

### Dual-Token Monitoring

The monitoring system uses a **two-step token exchange**:
1. The monitoring officer logs in with their standard credentials → receives a standard JWT.
2. They exchange the standard JWT + a server-side API key → receive a short-lived monitoring token (1 hour).

The `/monitoring/attendance` endpoint validates `token_type == "monitoring"` and rejects standard JWTs. This adds defense-in-depth: even if a monitoring officer's password is compromised, the attacker also needs the API key.

---

## Token Rotation & Revocation

In the current implementation, JWT tokens are **stateless** — once issued, they're valid until expiry. In a production deployment:

1. **Token Blacklisting:** Maintain a Redis set of revoked token JTIs (JWT IDs). Check this set in the `decode_token` function before accepting any token. Add a `jti` (unique ID) claim to each token.

2. **Refresh Token Pattern:** Issue short-lived access tokens (15 min) alongside long-lived refresh tokens stored in the database. When a user logs out or is deactivated, delete their refresh token.

3. **Monitoring API Key Rotation:** Store the `MONITORING_API_KEY` in a secrets manager (e.g., AWS Secrets Manager, HashiCorp Vault). Rotate quarterly and update via CI/CD pipeline without code changes.

4. **Emergency Revocation:** Change the `SECRET_KEY` to immediately invalidate ALL issued tokens. This is a nuclear option but effective for breach response.

---

## Security Considerations

### Known Issue: No Rate Limiting

**Problem:** The login and signup endpoints have no rate limiting. An attacker can brute-force passwords by sending thousands of login attempts per second.

**Fix:** Add rate limiting middleware using `slowapi` or similar:

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/auth/login")
@limiter.limit("5/minute")
def login(request: Request, body: LoginRequest, ...):
    ...
```

Additionally:
- Add account lockout after N failed attempts
- Implement CAPTCHA for signup
- Use HTTPS in production (Render handles this)
- Validate `Content-Type` headers
- Set CORS origins explicitly (not `*`)

---

## Project Status

### ✅ Fully Working

- All 5 user roles with proper RBAC
- JWT signup/login with bcrypt password hashing
- Dual-token monitoring flow
- Batch CRUD with invite-token-based enrollment
- Session creation with batch membership validation
- Attendance marking with enrollment validation
- Per-session, per-batch, per-institution, and programme-wide summaries
- Monitoring endpoint with 405 for non-GET methods
- Seed script with realistic sample data
- 5 integration tests with real database
- Render deployment configuration
- Auto table creation on startup

### ⚠️ Partial / Not Included

- **No Alembic migrations** — uses `create_all()` for simplicity (as specified)
- **No pagination** — summary endpoints return full datasets; would need `limit`/`offset` for production scale
- **No rate limiting** — see security section above
- **No refresh tokens** — using long-lived (24hr) access tokens only
- **No email verification** — signup accepts any email format without sending verification

### 🚫 Deliberately Skipped

- Alembic migrations (per requirements)
- Frontend/UI
- WebSocket real-time updates
- File upload/storage
- Notification system
