from datetime import datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field
from app.domains.auth.models import UserRole


class RegisterRequest(BaseModel):
    """
    Request model for user registration.
    Carries filled-in examples for interactive /docs OpenAPI exploration.
    """
    email: EmailStr = Field(..., examples=["donor@example.com"])
    password: str = Field(..., min_length=8, examples=["SecurePass123!"])
    role: UserRole = Field(default=UserRole.DONOR, examples=[UserRole.DONOR.value])
    phone: Optional[str] = Field(default=None, examples=["+2348012345678"])


class LoginRequest(BaseModel):
    """
    Request model for user sign-in.
    """
    email: EmailStr = Field(..., examples=["donor@example.com"])
    password: str = Field(..., examples=["SecurePass123!"])


class UserResponse(BaseModel):
    """
    Response model for user info.
    Security rule: NEVER exposes password_hash or internal secrets.
    """
    model_config = ConfigDict(from_attributes=True)

    id: int
    email: EmailStr
    role: str
    is_active: bool
    created_at: datetime


class TokenResponse(BaseModel):
    """
    Response model returning JWT access token upon successful authentication.
    """
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
