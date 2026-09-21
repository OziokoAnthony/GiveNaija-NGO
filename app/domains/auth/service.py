from sqlmodel import Session, select
from fastapi import status

from app.core.errors import AppException
from app.core.security import hash_password, verify_password, create_access_token
from app.domains.auth.models import User, Member, UserRole
from app.domains.auth.schemas import RegisterRequest, LoginRequest, TokenResponse, UserResponse
from app.domains.audit.models import AuditLog


class AuthService:
    """
    Business logic layer for Authentication and User management.
    Ensures all mutations execute in a single atomic transaction.
    """

    @staticmethod
    def register_user(session: Session, data: RegisterRequest) -> User:
        # Check if email is already in use
        normalized_email = data.email.strip().lower()
        existing = session.exec(
            select(User).where(User.email == normalized_email)
        ).first()

        if existing:
            raise AppException(
                status_code=status.HTTP_409_CONFLICT,
                code="EMAIL_ALREADY_EXISTS",
                message=f"User with email '{normalized_email}' already exists.",
            )

        try:
            # 1. Create User
            user = User(
                email=normalized_email,
                password_hash=hash_password(data.password),
                role=data.role.value,
                is_active=True,
            )
            session.add(user)
            session.flush()  # Generates user.id without committing

            # 2. If donor, create Member record
            if user.role == UserRole.DONOR.value:
                member = Member(
                    user_id=user.id,
                    phone=data.phone,
                )
                session.add(member)

            # 3. Write immutable audit log entry in the SAME transaction
            audit_entry = AuditLog(
                actor_id=user.id,
                action="USER_REGISTERED",
                target_type="users",
                target_id=user.id,
                details=f"Registered account with role '{user.role}'",
            )
            session.add(audit_entry)

            # Commit atomic transaction
            session.commit()
            session.refresh(user)
            return user
        except Exception:
            session.rollback()
            raise

    @staticmethod
    def authenticate_user(session: Session, data: LoginRequest) -> TokenResponse:
        normalized_email = data.email.strip().lower()
        user = session.exec(
            select(User).where(User.email == normalized_email)
        ).first()

        if not user or not verify_password(data.password, user.password_hash):
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="INVALID_CREDENTIALS",
                message="Invalid email or password.",
            )

        if not user.is_active:
            raise AppException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                code="ACCOUNT_INACTIVE",
                message="Your account has been deactivated. Please contact an administrator.",
            )

        token = create_access_token(
            subject=user.email,
            role=user.role,
            user_id=user.id,
        )

        return TokenResponse(
            access_token=token,
            token_type="bearer",
            user=UserResponse.model_validate(user),
        )
