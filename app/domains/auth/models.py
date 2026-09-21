from datetime import datetime, timezone
from enum import Enum
from typing import Optional
from sqlmodel import Field, SQLModel


class UserRole(str, Enum):
    """The three user roles required by GiveNaija."""
    DONOR = "donor"
    FINANCE = "finance"
    ADMIN = "admin"


class User(SQLModel, table=True):
    """
    User entity for authentication and authorization.
    Passwords are stored as bcrypt hashes; never in plaintext.
    """
    __tablename__ = "users"

    id: Optional[int] = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True, nullable=False)
    password_hash: str = Field(nullable=False)
    role: str = Field(default=UserRole.DONOR.value, nullable=False)
    is_active: bool = Field(default=True, nullable=False)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class Member(SQLModel, table=True):
    """
    Member profile associated with a donor user account.
    """
    __tablename__ = "members"

    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(foreign_key="users.id", unique=True, nullable=False)
    phone: Optional[str] = Field(default=None, nullable=True)
    joined_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
