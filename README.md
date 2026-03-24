# Curs Marking (MVP)

Desktop MVP-приложение для локального учета и печати кодов маркировки по ТЗ.

## Что реализовано
- Авторизация пользователей (роль + активность).
- Инициализация БД и дефолтного администратора `admin/admin`.
- Справочник товаров.
- Расчет доступных кодов.
- Создание задания на печать с транзакционным резервированием кодов.
- Завершение печати (перевод кодов в `printed`).
- Stub-импорт PDF (создание импорта + демо-парсинг).
- Журнал аудита действий.

## Быстрый старт
```bash
python -m venv .venv
source .venv/bin/activate
pip install -e .
python -m app.main
```


### Быстрый запуск в Windows (.bat)
```bat
scripts\run_windows.bat
```
Скрипт автоматически: создаст `.venv`, установит зависимости и запустит приложение.

## Архитектура
```text
app/
  main.py
  db/
    database.py
    models.py
  services/
    auth_service.py
    audit_service.py
    bootstrap.py
    config_service.py
    pdf_import_service.py
    print_job_service.py
    product_service.py
  utils/
    security.py
```

## Ограничения текущего MVP
- Реализован sqlite-режим (PostgreSQL можно добавить через `ConfigService`).
- Парсинг PDF пока заглушка (`parse_stub`) без реального Data Matrix-распознавания.
- Печать физически не отправляется на Windows-принтеры (статусы и workflow реализованы).
