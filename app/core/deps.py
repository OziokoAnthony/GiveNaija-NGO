from typing import Callable, List
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlmodel import Session

from app.core.security import decode_access_token, verify_cron_api_key
from app.db.session import get_db
from app.domains.auth.models import User, UserRole

# HTTP Bearer authentication scheme
security_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    session: Session = Depends(get_db),
) -> User:
    """
    Dependency that extracts, decodes, and validates the JWT token.
    Raises 401 Unauthorized if missing, malformed, expired, or user not found.
    """
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required. Missing Bearer token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload.get("user_id")
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token payload missing user identifier.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = session.get(User, user_id)
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account does not exist or is inactive.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


def require_role(*allowed_roles: str) -> Callable[[User], User]:
    """
    Role-Based Access Control (RBAC) dependency factory.
    Enforces authorization: raises 403 Forbidden if user's role is not permitted.
    """
    def role_checker(current_user: User = Depends(get_current_user)) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden. Requires one of roles: {', '.join(allowed_roles)}",
            )
        return current_user

    return role_checker


# Convenient pre-configured role dependencies
require_admin = require_role(UserRole.ADMIN.value)
require_finance = require_role(UserRole.FINANCE.value, UserRole.ADMIN.value)
require_donor = require_role(
    UserRole.DONOR.value,
    UserRole.FINANCE.value,
    UserRole.ADMIN.value,
)


def verify_cron_trigger(
    x_api_key: str = Header(..., alias="X-API-Key"),
) -> None:
    """
    Validates API key for scheduled background sweeps.
    Raises 401 Unauthorized if invalid.
    """
    if not verify_cron_api_key(x_api_key):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing cron API key.",
        )
