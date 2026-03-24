from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import Product


class ProductService:
    @staticmethod
    def list_products(session: Session) -> list[Product]:
        return list(session.scalars(select(Product).order_by(Product.name)).all())

    @staticmethod
    def create_product(
        session: Session,
        name: str,
        sku: str | None = None,
        gtin: str | None = None,
        category: str | None = None,
    ) -> Product:
        product = Product(name=name, sku=sku, gtin=gtin, category=category)
        session.add(product)
        session.flush()
        return product
