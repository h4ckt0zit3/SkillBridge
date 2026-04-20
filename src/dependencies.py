"""
dependencies.py — Reusable FastAPI dependencies for authentication and role-based access control.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError

from src.auth import decode_token

# HTTP Bearer scheme — extracts token from the Authorization header
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
) -> dict:
    """
    Dependency that extracts and validates the JWT from the Authorization header.

    Returns:
        dict with keys: user_id (int), role (str), token_type (str).

    Raises:
        401 if token is missing, expired, or invalid.
    """
    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Provide a Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    try:
        payload = decode_token(credentials.credentials)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    role = payload.get("role")
    token_type = payload.get("token_type", "standard")

    if user_id is None or role is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload is missing required fields.",
        )

    return {"user_id": user_id, "role": role, "token_type": token_type}


def require_role(*roles: str):
    """
    Factory that returns a dependency enforcing that the current user's role
    is one of the specified allowed roles.

    Usage:
        @router.get("/admin-only", dependencies=[Depends(require_role("institution"))])

    Or inject the user dict:
        current_user: dict = Depends(require_role("trainer", "institution"))
    """

    def role_checker(current_user: dict = Depends(get_current_user)) -> dict:
        if current_user["role"] not in roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role(s): {', '.join(roles)}. Your role: {current_user['role']}.",
            )
        return current_user

    return role_checker
