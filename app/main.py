from __future__ import annotations

from dataclasses import dataclass

import flet as ft
from sqlalchemy import select

from app.db.database import Database
from app.db.models import AuditLog, JobStatus, PrintJob, Product, User
from app.services.auth_service import AuthService
from app.services.bootstrap import bootstrap_data
from app.services.config_service import ConfigService
from app.services.pdf_import_service import PdfImportService
from app.services.print_job_service import PrintJobService
from app.services.product_service import ProductService


@dataclass
class AppState:
    user: User | None = None


def main(page: ft.Page) -> None:
    page.title = "Curs Marking"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.window_width = 1200
    page.window_height = 800
    page.padding = 16

    config = ConfigService.load()
    ConfigService.save(config)
    db = Database(ConfigService.make_db_url(config))
    db.create_all()

    with db.session() as session:
        bootstrap_data(session)

    state = AppState()

    login_field = ft.TextField(label="Логин", width=320, autofocus=True)
    password_field = ft.TextField(label="Пароль", password=True, can_reveal_password=True, width=320)
    message = ft.Text(color=ft.Colors.RED_600)

    def load_dashboard() -> None:
        assert state.user
        page.clean()

        user_title = ft.Text(f"Пользователь: {state.user.full_name} ({state.user.role.value})")
        logout_btn = ft.ElevatedButton("Выйти", on_click=lambda _: show_login())

        products_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("ID")),
                ft.DataColumn(ft.Text("Наименование")),
                ft.DataColumn(ft.Text("SKU")),
                ft.DataColumn(ft.Text("GTIN")),
            ],
            rows=[],
        )

        product_name = ft.TextField(label="Наименование")
        product_sku = ft.TextField(label="SKU")
        product_gtin = ft.TextField(label="GTIN")

        def refresh_products() -> None:
            with db.session() as session:
                products = ProductService.list_products(session)
            products_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(str(p.id))),
                        ft.DataCell(ft.Text(p.name)),
                        ft.DataCell(ft.Text(p.sku or "")),
                        ft.DataCell(ft.Text(p.gtin or "")),
                    ]
                )
                for p in products
            ]
            page.update()

        def add_product(_: ft.ControlEvent) -> None:
            if not product_name.value.strip():
                return
            with db.session() as session:
                ProductService.create_product(
                    session,
                    name=product_name.value.strip(),
                    sku=product_sku.value.strip() or None,
                    gtin=product_gtin.value.strip() or None,
                )
            product_name.value = ""
            product_sku.value = ""
            product_gtin.value = ""
            refresh_products()

        refresh_products()

        products_view = ft.Column(
            [
                ft.Text("Справочник товаров", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([product_name, product_sku, product_gtin, ft.ElevatedButton("Добавить", on_click=add_product)]),
                products_table,
            ],
            scroll=ft.ScrollMode.AUTO,
        )

        print_product = ft.Dropdown(label="Товар", width=400)
        print_qty = ft.TextField(label="Количество", value="10", width=160)
        print_printer = ft.TextField(label="Принтер", value="Default Printer", width=300)
        print_template = ft.TextField(label="Шаблон", value="A4-1", width=180)
        print_status = ft.Text()
        print_counts = ft.Text()

        def refresh_print_products() -> None:
            with db.session() as session:
                products = list(session.scalars(select(Product).order_by(Product.name)).all())
            print_product.options = [ft.dropdown.Option(str(p.id), p.name) for p in products]
            if products and not print_product.value:
                print_product.value = str(products[0].id)
            page.update()

        def show_counts(_: ft.ControlEvent | None = None) -> None:
            if not print_product.value:
                return
            with db.session() as session:
                counts = PrintJobService.calculate_counts(session, int(print_product.value))
            print_counts.value = (
                f"Всего: {counts['total']} | Доступно: {counts['available']} | "
                f"Резерв: {counts['reserved_for_print']} | Напечатано: {counts['printed']}"
            )
            page.update()

        def create_job(_: ft.ControlEvent) -> None:
            if not print_product.value:
                return
            try:
                qty = int(print_qty.value)
            except (TypeError, ValueError):
                print_status.value = "Некорректное количество"
                print_status.color = ft.Colors.RED_600
                page.update()
                return

            with db.session() as session:
                job = PrintJobService.create_print_job(
                    session,
                    product_id=int(print_product.value),
                    batch_id=None,
                    requested_qty=qty,
                    printer_name=print_printer.value or "Default Printer",
                    template_name=print_template.value or "A4-1",
                    created_by=state.user.id,
                )
            print_status.value = f"Задание #{job.id} создано и зарезервировано {qty} кодов"
            print_status.color = ft.Colors.GREEN_700
            show_counts()

        def mark_printed(_: ft.ControlEvent) -> None:
            with db.session() as session:
                job = session.scalar(
                    select(PrintJob).where(PrintJob.status == JobStatus.created).order_by(PrintJob.id.desc())
                )
                if not job:
                    print_status.value = "Нет созданных заданий для завершения"
                    print_status.color = ft.Colors.RED_600
                else:
                    PrintJobService.mark_printed(session, job)
                    print_status.value = f"Задание #{job.id} завершено"
                    print_status.color = ft.Colors.GREEN_700
            show_counts()
            page.update()

        refresh_print_products()
        show_counts()

        print_view = ft.Column(
            [
                ft.Text("Печать", size=20, weight=ft.FontWeight.BOLD),
                ft.Row([print_product, ft.ElevatedButton("Обновить остатки", on_click=show_counts)]),
                print_counts,
                ft.Row([print_qty, print_printer, print_template]),
                ft.Row(
                    [
                        ft.ElevatedButton("Создать задание", on_click=create_job),
                        ft.OutlinedButton("Отметить последнее задание как напечатанное", on_click=mark_printed),
                    ]
                ),
                print_status,
                ft.Text(
                    "MVP: отправка на физический принтер и генерация Data Matrix будут добавлены в следующем шаге."
                ),
            ]
        )

        import_path = ft.TextField(label="Путь к PDF на локальном ПК", width=650)
        import_msg = ft.Text()

        def run_import(_: ft.ControlEvent) -> None:
            path = (import_path.value or "").strip()
            if not path:
                import_msg.value = "Укажите путь к PDF"
                import_msg.color = ft.Colors.RED_600
                page.update()
                return
            try:
                with db.session() as session:
                    imported = PdfImportService.create_import_record(
                        session,
                        source_file=path,
                        storage_root=config.storage_path,
                        user_id=state.user.id,
                    )
                    PdfImportService.parse_stub(session, imported)
                import_msg.value = f"Импорт #{imported.id} завершен (stub-парсер): saved={imported.total_saved}"
                import_msg.color = ft.Colors.GREEN_700
            except Exception as exc:
                import_msg.value = f"Ошибка импорта: {exc}"
                import_msg.color = ft.Colors.RED_600
            page.update()

        imports_view = ft.Column(
            [
                ft.Text("Импорт PDF", size=20, weight=ft.FontWeight.BOLD),
                ft.Text("Для MVP используется stub-парсер (демонстрационный)."),
                ft.Row([import_path, ft.ElevatedButton("Загрузить", on_click=run_import)]),
                import_msg,
            ]
        )

        audit_table = ft.DataTable(
            columns=[
                ft.DataColumn(ft.Text("Время")),
                ft.DataColumn(ft.Text("Событие")),
                ft.DataColumn(ft.Text("Объект")),
                ft.DataColumn(ft.Text("Сообщение")),
            ],
            rows=[],
        )

        def refresh_audit() -> None:
            with db.session() as session:
                logs = list(session.scalars(select(AuditLog).order_by(AuditLog.id.desc()).limit(50)).all())
            audit_table.rows = [
                ft.DataRow(
                    cells=[
                        ft.DataCell(ft.Text(log.created_at.strftime("%Y-%m-%d %H:%M:%S"))),
                        ft.DataCell(ft.Text(log.event_type)),
                        ft.DataCell(ft.Text(f"{log.entity_type}:{log.entity_id or '-'}")),
                        ft.DataCell(ft.Text(log.message)),
                    ]
                )
                for log in logs
            ]
            page.update()

        refresh_audit()

        audit_view = ft.Column(
            [
                ft.Text("Журнал действий", size=20, weight=ft.FontWeight.BOLD),
                ft.ElevatedButton("Обновить", on_click=lambda _: refresh_audit()),
                audit_table,
            ],
            scroll=ft.ScrollMode.AUTO,
        )

        tabs = ft.Tabs(
            selected_index=0,
            animation_duration=200,
            tabs=[
                ft.Tab(text="Товары", content=products_view),
                ft.Tab(text="Печать", content=print_view),
                ft.Tab(text="Импорт PDF", content=imports_view),
                ft.Tab(text="Аудит", content=audit_view),
            ],
            expand=1,
        )

        page.add(ft.Row([user_title, logout_btn], alignment=ft.MainAxisAlignment.SPACE_BETWEEN), tabs)

    def try_login(_: ft.ControlEvent) -> None:
        login = login_field.value.strip()
        password = password_field.value
        with db.session() as session:
            user = AuthService.login(session, login, password)
        if not user:
            message.value = "Ошибка авторизации"
            page.update()
            return
        state.user = user
        load_dashboard()

    def show_login() -> None:
        state.user = None
        login_field.value = ""
        password_field.value = ""
        message.value = ""
        page.clean()
        page.add(
            ft.Column(
                [
                    ft.Text("Curs Marking", size=32, weight=ft.FontWeight.BOLD),
                    ft.Text("Вход в систему"),
                    login_field,
                    password_field,
                    ft.ElevatedButton("Войти", on_click=try_login),
                    ft.Text("Дефолт: admin / admin"),
                    message,
                ],
                horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                alignment=ft.MainAxisAlignment.CENTER,
                expand=True,
            )
        )

    show_login()


if __name__ == "__main__":
    ft.app(target=main)
