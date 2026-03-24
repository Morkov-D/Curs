from __future__ import annotations

import shutil
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db.models import CodeStatus, MarkingCode, PdfImport


class PdfImportService:
    @staticmethod
    def create_import_record(
        session: Session,
        *,
        source_file: str,
        storage_root: str,
        user_id: int,
    ) -> PdfImport:
        src = Path(source_file)
        storage_dir = Path(storage_root) / "pdf"
        storage_dir.mkdir(parents=True, exist_ok=True)
        target = storage_dir / src.name
        shutil.copy2(src, target)

        item = PdfImport(file_name=src.name, file_path=str(target), uploaded_by=user_id, parse_status="pending")
        session.add(item)
        session.flush()
        return item

    @staticmethod
    def parse_stub(session: Session, import_row: PdfImport, product_id: int | None = None) -> PdfImport:
        # MVP stub: вместо реального распознавания создает несколько демо-кодов по имени файла.
        import_row.parse_status = "done"
        import_row.total_found = 5
        import_row.total_errors = 0

        saved = 0
        duplicates = 0
        for idx in range(1, 6):
            raw_code = f"{import_row.file_name}-RAW-{idx:04d}"
            exists = session.scalar(select(MarkingCode.id).where(MarkingCode.raw_code == raw_code))
            if exists:
                duplicates += 1
                continue
            session.add(
                MarkingCode(
                    product_id=product_id,
                    source_pdf_id=import_row.id,
                    source_page=idx,
                    raw_code=raw_code,
                    status=CodeStatus.available,
                )
            )
            saved += 1

        import_row.total_saved = saved
        import_row.total_duplicates = duplicates
        return import_row
