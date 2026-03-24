# ТЗ (прикладной формат)

Документ разворачивает базовое ТЗ в формат: **экраны + БД + сервисы/API + пользовательские сценарии** для оценки трудоемкости и начала проектирования.

## 1) Экраны и действия пользователя

## 1.1 Экран входа
**Поля:** login, password.  
**Действия:** войти, показать ошибку авторизации.  
**Права:** все роли.

## 1.2 Главный экран (навигация)
Разделы: Импорт PDF, Коды, Печать, История печати, Отчеты, Настройки, Пользователи.

## 1.3 Импорт PDF
**Функции:**
- выбрать файл;
- загрузить;
- увидеть запись импорта и статус парсинга;
- открыть результат (коды/ошибки);
- фильтровать импорты по статусам.

**Ограничение прав:** администратор и оператор импорта.

## 1.4 Коды
**Фильтры:** товар, дата производства, партия, статус, текст кода.  
**Карточка кода:** raw_code, статус, источник, номер страницы, партия, товар, reprint_count.  
**Ручные операции:** корректировка данных, ручная смена статуса (по правам), пометка как spoiled.

## 1.5 Печать
**Шаги:**
1. Выбор товара/даты/партии.
2. Показ остатков (available/reserved/printed/spoiled).
3. Ввод количества.
4. Выбор принтера и шаблона.
5. Предпросмотр.
6. Запуск печати.

## 1.6 История печати
**Список:** задания с фильтрами по пользователю, товару, статусу.  
**Детали:** состав `print_job_items`, ошибки, время печати.  
**Действия:** отмена (по правам), повторная печать (по правам, с причиной).

## 1.7 Администрирование
- Пользователи и роли;
- Товары;
- Шаблоны печати;
- Принтеры;
- Системные настройки;
- Резервное копирование.

---

## 2) Модель данных (минимум для MVP)

## 2.1 Основные таблицы
- `users`
- `products`
- `batches`
- `pdf_imports`
- `marking_codes`
- `print_jobs`
- `print_job_items`
- `audit_log`

## 2.2 Ключевые связи
- `batches.product_id -> products.id`
- `marking_codes.product_id -> products.id`
- `marking_codes.batch_id -> batches.id`
- `marking_codes.source_pdf_id -> pdf_imports.id`
- `print_jobs.product_id -> products.id`
- `print_jobs.batch_id -> batches.id`
- `print_job_items.print_job_id -> print_jobs.id`
- `print_job_items.marking_code_id -> marking_codes.id`

## 2.3 Критические ограничения
- `marking_codes.raw_code` — UNIQUE;
- Индекс: `(product_id, batch_id, status)`;
- Индекс для выборки доступных кодов: `(status, product_id, batch_id, id)`.

---

## 3) Сервисы и API-контракты (слой приложения)

Ниже — **внутренние сервисы** (Python), при необходимости могут быть обернуты в локальный HTTP API.

## 3.1 `auth_service`
- `login(login, password) -> session/user`
- `create_user(...)`
- `change_password(...)`
- `disable_user(...)`

## 3.2 `config_service`
- `save_db_config(...)`
- `test_connection(...)`
- `init_database(...)`
- `init_storage_dirs(...)`

## 3.3 `pdf_import_service`
- `create_import(file, user_id) -> import_id`
- `run_parse(import_id)`
- `get_import_status(import_id)`

## 3.4 `code_parser_service`
- `extract_codes_from_pdf(path) -> list[ParsedCode]`
- `normalize_raw_code(raw) -> normalized`
- `split_fields(raw) -> gtin/serial/crypto...`

## 3.5 `print_job_service`
- `calculate_available(product_id, date, batch_id=None)`
- `create_print_job(request)` **(транзакционно)**
- `mark_print_success(job_id)`
- `mark_print_failed(job_id, reason)`
- `cancel_job(job_id)`

## 3.6 `printer_service`
- `list_system_printers()`
- `render_labels(job_id, template_id, format='PDF|PNG')`
- `send_to_printer(file, printer, settings)`

## 3.7 `reprint_service`
- `create_reprint(marking_code_id|job_id, reason_id, comment, user_id)`
- `increment_reprint_counter(marking_code_id)`

## 3.8 `audit_service`
- `log_event(user_id, event_type, entity_type, entity_id, message)`

---

## 4) Ключевые сценарии (Use Cases)

## UC-01 Импорт PDF
1. Оператор выбирает файл.
2. Система копирует файл в сетевое хранилище.
3. Создает `pdf_imports`.
4. Запускает парсинг.
5. Для каждого кода: проверка дубля, привязка к товару/партии, запись в `marking_codes`.
6. Формирует итог: `total_found/saved/duplicates/errors`.

## UC-02 Создание задания на печать
1. Пользователь выбирает товар/дату/партию, указывает qty.
2. Система проверяет доступный остаток.
3. В одной транзакции:
   - выбирает `available` коды (`FOR UPDATE SKIP LOCKED` для PostgreSQL);
   - переводит их в `reserved_for_print`;
   - создает `print_jobs`;
   - создает `print_job_items`.
4. Генерирует этикетки.
5. Отправляет на принтер.
6. Успех: статусы кодов -> `printed`, job -> `printed`.
7. Ошибка: job -> `failed`; статусы откатываются/переводятся в ручную обработку по этапу сбоя.

## UC-03 Повторная печать
1. Пользователь с правами выбирает код/задание.
2. Указывает причину.
3. Система создает отдельное задание повторной печати на тот же `raw_code`.
4. Увеличивает `reprint_count` и пишет событие в аудит.

---

## 5) Правила статусов и переходов

```text
imported -> available -> reserved_for_print -> printed
                         \-> cancelled (при отмене до фактической печати)
printed -> reprinted (по контролируемому сценарию)
* -> spoiled / error (по результатам операций и ручных действий)
```

Ограничения:
- Нельзя печатать коды вне `available`.
- Нельзя резервировать один и тот же код в двух заданиях.
- Ручная смена статусов — только у администратора.

---

## 6) Разбиение по релизам

## MVP (Этап 1)
- Авторизация и роли;
- Подключение к БД;
- Справочник товаров;
- Импорт PDF и парсинг;
- Экран кодов;
- Расчет доступного количества;
- Создание и выполнение задания печати;
- Базовая история заданий.

## Этап 2
- Партии;
- Шаблоны печати;
- Повторная печать и причины;
- Полный аудит;
- Экспорт отчетов;
- Ручная корректировка импорта.

## Этап 3
- ZPL/TSPL;
- Расширенная аналитика;
- Массовые сервисные операции;
- Уведомления администратору.

---

## 7) Что оценивать в первую очередь

1. Транзакционная логика резервирования/печати.
2. Качество извлечения Data Matrix из разных типов PDF.
3. Скорость пакетной печати до 5000 кодов.
4. UX ручной корректировки при проблемных импортах.
5. Надежность отката статусов и ведение аудита.

