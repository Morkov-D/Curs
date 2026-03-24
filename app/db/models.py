from __future__ import annotations

import datetime as dt
import enum

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class UserRole(str, enum.Enum):
    admin = "admin"
    import_operator = "import_operator"
    print_operator = "print_operator"
    viewer = "viewer"


class CodeStatus(str, enum.Enum):
    imported = "imported"
    available = "available"
    reserved_for_print = "reserved_for_print"
    printed = "printed"
    reprinted = "reprinted"
    applied = "applied"
    spoiled = "spoiled"
    cancelled = "cancelled"
    error = "error"


class JobStatus(str, enum.Enum):
    created = "created"
    printing = "printing"
    printed = "printed"
    failed = "failed"
    cancelled = "cancelled"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    login: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[UserRole] = mapped_column(Enum(UserRole), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    sku: Mapped[str | None] = mapped_column(String(64))
    gtin: Mapped[str | None] = mapped_column(String(32))
    category: Mapped[str | None] = mapped_column(String(64))
    description: Mapped[str | None] = mapped_column(Text)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class Batch(Base):
    __tablename__ = "batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    production_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    batch_number: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class PdfImport(Base):
    __tablename__ = "pdf_imports"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    file_name: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(String(512), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    parse_status: Mapped[str] = mapped_column(String(32), default="pending", nullable=False)
    total_found: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_saved: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_duplicates: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_errors: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    note: Mapped[str | None] = mapped_column(Text)


class MarkingCode(Base):
    __tablename__ = "marking_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int | None] = mapped_column(ForeignKey("products.id"))
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    raw_code: Mapped[str] = mapped_column(String(512), nullable=False, unique=True)
    gtin: Mapped[str | None] = mapped_column(String(32))
    serial: Mapped[str | None] = mapped_column(String(128))
    crypto_91: Mapped[str | None] = mapped_column(String(128))
    crypto_92: Mapped[str | None] = mapped_column(String(128))
    source_pdf_id: Mapped[int | None] = mapped_column(ForeignKey("pdf_imports.id"))
    source_page: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[CodeStatus] = mapped_column(Enum(CodeStatus), default=CodeStatus.imported)
    reprint_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    printed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime, default=func.now(), onupdate=func.now(), nullable=False
    )


class PrintJob(Base):
    __tablename__ = "print_jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), nullable=False)
    batch_id: Mapped[int | None] = mapped_column(ForeignKey("batches.id"))
    requested_qty: Mapped[int] = mapped_column(Integer, nullable=False)
    reserved_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    printed_qty: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    printer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    template_name: Mapped[str] = mapped_column(String(255), nullable=False)
    print_settings_json: Mapped[str | None] = mapped_column(Text)
    status: Mapped[JobStatus] = mapped_column(Enum(JobStatus), default=JobStatus.created, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
    printed_at: Mapped[dt.datetime | None] = mapped_column(DateTime)
    error_message: Mapped[str | None] = mapped_column(Text)

    items: Mapped[list["PrintJobItem"]] = relationship(back_populates="job", cascade="all, delete")


class PrintJobItem(Base):
    __tablename__ = "print_job_items"
    __table_args__ = (UniqueConstraint("print_job_id", "marking_code_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    print_job_id: Mapped[int] = mapped_column(ForeignKey("print_jobs.id"), nullable=False)
    marking_code_id: Mapped[int] = mapped_column(ForeignKey("marking_codes.id"), nullable=False)
    raw_code: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="reserved", nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)

    job: Mapped[PrintJob] = relationship(back_populates="items")


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(64))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)


class ReprintReason(Base):
    __tablename__ = "reprint_reasons"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False, unique=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class ReprintEvent(Base):
    __tablename__ = "reprint_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    marking_code_id: Mapped[int] = mapped_column(ForeignKey("marking_codes.id"), nullable=False)
    print_job_id: Mapped[int | None] = mapped_column(ForeignKey("print_jobs.id"))
    reason_id: Mapped[int] = mapped_column(ForeignKey("reprint_reasons.id"), nullable=False)
    comment: Mapped[str | None] = mapped_column(Text)
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=func.now(), nullable=False)
