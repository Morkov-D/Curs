from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import User, UserRole
from app.services.audit_service import AuditService
from app.utils.security import hash_password, verify_password


class AuthService:
    @staticmethod
    def ensure_admin(session: Session) -> None:
        exists = session.scalar(select(User).where(User.role == UserRole.admin))
        if exists:
            return
        user = User(
            login="admin",
            password_hash=hash_password("admin"),
            full_name="Администратор",
            role=UserRole.admin,
            is_active=True,
        )
        session.add(user)
        session.flush()
        AuditService.log(
            session,
            user.id,
            "bootstrap",
            "user",
            str(user.id),
            "Создан дефолтный администратор admin/admin",
        )

    @staticmethod
    def login(session: Session, login: str, password: str) -> User | None:
        user = session.scalar(select(User).where(User.login == login))
        if not user or not user.is_active:
            return None
        if not verify_password(password, user.password_hash):
            return None
        AuditService.log(session, user.id, "login", "user", str(user.id), "Успешный вход")
        return user
