from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CodeStatus, MarkingCode, Product, ReprintReason
from app.services.auth_service import AuthService


def bootstrap_data(session: Session) -> None:
    AuthService.ensure_admin(session)

    reasons = [
        "брак печати",
        "смещение",
        "повреждение этикетки",
        "тестовая печать",
        "замена носителя",
    ]
    for reason_name in reasons:
        exists = session.scalar(select(ReprintReason).where(ReprintReason.name == reason_name))
        if not exists:
            session.add(ReprintReason(name=reason_name, is_active=True))

    has_products = session.scalar(select(Product.id).limit(1))
    if has_products:
        return

    demo = Product(name="Демо товар", sku="DEMO-001", gtin="04600000000000", category="demo")
    session.add(demo)
    session.flush()

    for idx in range(1, 31):
        raw = f"010460000000000021DEMO{idx:06d}91ABCD92EFGH"
        session.add(
            MarkingCode(
                product_id=demo.id,
                raw_code=raw,
                gtin="04600000000000",
                serial=f"DEMO{idx:06d}",
                status=CodeStatus.available,
            )
        )
