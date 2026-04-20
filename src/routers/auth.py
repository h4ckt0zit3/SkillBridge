"""
routers/auth.py — Authentication endpoints (signup, login, monitoring token).
"""

from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DBSession

from src.database import get_db
from src.models import User, UserRole
from src.schemas import SignupRequest, LoginRequest, MonitoringTokenRequest, TokenResponse
from src.auth import hash_password, verify_password, create_access_token, MONITORING_API_KEY
from src.dependencies import get_current_user, require_role

router = APIRouter(prefix="/auth", tags=["Auth"])


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def signup(body: SignupRequest, db: DBSession = Depends(get_db)):
    """
    Register a new user account.

    - Validates the role is one of the 5 allowed roles.
    - Checks that the email is not already registered.
    - Hashes the password with bcrypt.
    - Returns a signed JWT.
    """
    # Validate role
    valid_roles = [r.value for r in UserRole]
    if body.role not in valid_roles:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid role '{body.role}'. Must be one of: {', '.join(valid_roles)}",
        )

    # Check for existing email
    existing = db.query(User).filter(User.email == body.email).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Email '{body.email}' is already registered.",
        )

    # Create the user
    user = User(
        name=body.name,
        email=body.email,
        hashed_password=hash_password(body.password),
        role=UserRole(body.role),
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Issue JWT
    token = create_access_token({"user_id": user.id, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/login", response_model=TokenResponse)
def login(body: LoginRequest, db: DBSession = Depends(get_db)):
    """
    Authenticate and receive a JWT (24hr expiry).

    Payload: { user_id, role, token_type: "standard", iat, exp }
    """
    user = db.query(User).filter(User.email == body.email).first()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
        )

    token = create_access_token({"user_id": user.id, "role": user.role.value})
    return TokenResponse(access_token=token)


@router.post("/monitoring-token", response_model=TokenResponse)
def monitoring_token(
    body: MonitoringTokenRequest,
    current_user: dict = Depends(require_role("monitoring_officer")),
):
    """
    Issue a short-lived monitoring token (1hr) for the /monitoring/* endpoints.

    Requires:
    - A valid standard JWT from a monitoring_officer.
    - The correct MONITORING_API_KEY in the request body.

    Payload: { user_id, role: "monitoring_officer", token_type: "monitoring", iat, exp }
    """
    if body.key != MONITORING_API_KEY:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid monitoring API key.",
        )

    token = create_access_token(
        data={
            "user_id": current_user["user_id"],
            "role": "monitoring_officer",
            "token_type": "monitoring",
        },
        expires_delta=timedelta(hours=1),
    )
    return TokenResponse(access_token=token)
