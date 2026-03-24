@echo off
setlocal EnableExtensions EnableDelayedExpansion

cd /d "%~dp0\.."

echo [1/4] Проверка Python...
where python >nul 2>&1
if errorlevel 1 (
  echo Python не найден в PATH. Установите Python 3.11+ и повторите.
  exit /b 1
)

echo [2/4] Создание venv (если отсутствует)...
if not exist ".venv\Scripts\python.exe" (
  python -m venv .venv
  if errorlevel 1 (
    echo Не удалось создать виртуальное окружение.
    exit /b 1
  )
)

echo [3/4] Установка зависимостей...
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
if errorlevel 1 (
  echo Предупреждение: не удалось обновить pip, продолжаем.
)

pip install -e .
if errorlevel 1 (
  echo Ошибка установки зависимостей. Проверьте доступ к интернету/прокси.
  exit /b 1
)

echo [4/4] Запуск приложения...
python -m app.main
set EXIT_CODE=%ERRORLEVEL%

call .venv\Scripts\deactivate.bat
exit /b %EXIT_CODE%
