from __future__ import annotations

from sqlalchemy.orm import Session

from app.db.models import AuditLog


class AuditService:
    @staticmethod
    def log(
        session: Session,
        user_id: int | None,
        event_type: str,
        entity_type: str,
        entity_id: str | None,
        message: str,
    ) -> None:
        session.add(
            AuditLog(
                user_id=user_id,
                event_type=event_type,
                entity_type=entity_type,
                entity_id=entity_id,
                message=message,
            )
        )
