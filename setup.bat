@echo off
REM Crea el entorno virtual e instala las dependencias.
REM Usa Python 3.12/3.13/3.11/3.10 si existe; si no, el Python que tengas (p. ej. 3.14).
cd /d "%~dp0"
set PYV=
for %%V in (3.12 3.13 3.11 3.10) do (
  if not defined PYV (
    py -%%V --version >nul 2>nul && set PYV=%%V
  )
)
if exist .venv rmdir /s /q .venv
if defined PYV (
  echo Usando Python %PYV%
  py -%PYV% -m venv .venv
) else (
  echo Usando el Python predeterminado del sistema
  python -m venv .venv
)
if errorlevel 1 (
  echo Error creando el entorno virtual. Comprueba que Python este instalado y en el PATH.
  pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install --only-binary=:all: -r requirements.txt
if errorlevel 1 (
  echo.
  echo ERROR: no se pudieron instalar las dependencias. Revisa los mensajes de arriba.
  pause
  exit /b 1
)
echo.
echo Listo. Ejecuta run.bat para iniciar la aplicacion.
pause
