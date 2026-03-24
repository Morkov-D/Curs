from __future__ import annotations

import datetime as dt

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.db.models import Batch, CodeStatus, JobStatus, MarkingCode, PrintJob, PrintJobItem
from app.services.audit_service import AuditService


class PrintJobService:
    @staticmethod
    def calculate_counts(session: Session, product_id: int, batch_id: int | None = None) -> dict[str, int]:
        query = select(MarkingCode.status, func.count(MarkingCode.id)).where(MarkingCode.product_id == product_id)
        if batch_id:
            query = query.where(MarkingCode.batch_id == batch_id)
        query = query.group_by(MarkingCode.status)
        rows = session.execute(query).all()

        result = {
            "total": 0,
            "available": 0,
            "reserved_for_print": 0,
            "printed": 0,
            "spoiled": 0,
            "cancelled": 0,
        }
        for status, qty in rows:
            key = status.value if isinstance(status, CodeStatus) else str(status)
            if key in result:
                result[key] = qty
            result["total"] += qty
        return result

    @staticmethod
    def create_print_job(
        session: Session,
        *,
        product_id: int,
        batch_id: int | None,
        requested_qty: int,
        printer_name: str,
        template_name: str,
        created_by: int,
    ) -> PrintJob:
        codes_query = (
            select(MarkingCode)
            .where(
                MarkingCode.product_id == product_id,
                MarkingCode.status == CodeStatus.available,
            )
            .order_by(MarkingCode.id)
            .limit(requested_qty)
            .with_for_update()
        )
        if batch_id:
            codes_query = codes_query.where(MarkingCode.batch_id == batch_id)

        selected_codes = list(session.scalars(codes_query).all())
        if len(selected_codes) < requested_qty:
            raise ValueError("Недостаточно доступных кодов для печати")

        job = PrintJob(
            product_id=product_id,
            batch_id=batch_id,
            requested_qty=requested_qty,
            reserved_qty=requested_qty,
            printer_name=printer_name,
            template_name=template_name,
            status=JobStatus.created,
            created_by=created_by,
        )
        session.add(job)
        session.flush()

        for code in selected_codes:
            code.status = CodeStatus.reserved_for_print
            session.add(
                PrintJobItem(
                    print_job_id=job.id,
                    marking_code_id=code.id,
                    raw_code=code.raw_code,
                    status="reserved",
                )
            )

        AuditService.log(
            session,
            created_by,
            "print_job_created",
            "print_job",
            str(job.id),
            f"Создано задание #{job.id} на {requested_qty} кодов",
        )
        return job

    @staticmethod
    def mark_printed(session: Session, job: PrintJob) -> None:
        job.status = JobStatus.printed
        job.printed_qty = job.reserved_qty
        job.printed_at = dt.datetime.utcnow()

        items = list(session.scalars(select(PrintJobItem).where(PrintJobItem.print_job_id == job.id)).all())
        for item in items:
            code = session.get(MarkingCode, item.marking_code_id)
            if not code:
                continue
            code.status = CodeStatus.printed
            code.printed_at = dt.datetime.utcnow()
            item.status = "printed"

        AuditService.log(
            session,
            job.created_by,
            "print_job_printed",
            "print_job",
            str(job.id),
            f"Задание #{job.id} успешно напечатано",
        )

    @staticmethod
    def create_batch(session: Session, product_id: int, production_date: dt.date, batch_number: str) -> Batch:
        batch = Batch(product_id=product_id, production_date=production_date, batch_number=batch_number)
        session.add(batch)
        session.flush()
        return batch
