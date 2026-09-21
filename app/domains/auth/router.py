from fastapi import APIRouter, Depends, status
from sqlmodel import Session

from app.db.session import get_db
from app.domains.auth.schemas import RegisterRequest, LoginRequest, UserResponse, TokenResponse
from app.domains.auth.service import AuthService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
    description="Registers a new donor or staff member. Donors automatically receive a member profile.",
)
def register(
    payload: RegisterRequest,
    session: Session = Depends(get_db),
) -> UserResponse:
    """Thin route handler delegating directly to AuthService."""
    user = AuthService.register_user(session=session, data=payload)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Authenticate and receive JWT token",
    description="Authenticates user credentials and returns a signed bearer JWT token containing user role and identity.",
)
def login(
    payload: LoginRequest,
    session: Session = Depends(get_db),
) -> TokenResponse:
    """Thin route handler delegating directly to AuthService."""
    return AuthService.authenticate_user(session=session, data=payload)
