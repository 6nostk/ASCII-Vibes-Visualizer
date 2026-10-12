@echo off
REM Genera la aplicacion portable con PyInstaller.
REM Uso: build_exe.bat [console]
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Primero ejecuta setup.bat para crear el entorno.
  if not defined BUILD_FROM_INSTALLER pause
  exit /b 1
)
if not exist "ASCII-Vibes-Visualizer.ico" (
  echo No se encuentra ASCII-Vibes-Visualizer.ico.
  if not defined BUILD_FROM_INSTALLER pause
  exit /b 1
)
if not exist "ASCII Vibes Visualizer logo.png" (
  echo No se encuentra ASCII Vibes Visualizer logo.png.
  if not defined BUILD_FROM_INSTALLER pause
  exit /b 1
)
call .venv\Scripts\activate.bat
python -c "import PyInstaller" >nul 2>nul
if errorlevel 1 (
  python -m pip install pyinstaller
  if errorlevel 1 (
    echo No se pudo instalar PyInstaller.
    if not defined BUILD_FROM_INSTALLER pause
    exit /b 1
  )
)
set MODE=--noconsole
if /i "%1"=="console" set MODE=--console
python -m PyInstaller --noconfirm --clean %MODE% --name ASCII-Vibes-Visualizer ^
  --icon "ASCII-Vibes-Visualizer.ico" ^
  --add-data "ASCII Vibes Visualizer logo.png;." ^
  --paths . --collect-all pygame --collect-all pyaudiowpatch --hidden-import asciiviz.app run.py
if errorlevel 1 (
  echo.
  echo ERROR al generar la aplicacion portable.
  if not defined BUILD_FROM_INSTALLER pause
  exit /b 1
)
echo.
echo Listo: dist\ASCII-Vibes-Visualizer\ASCII-Vibes-Visualizer.exe
if not defined BUILD_FROM_INSTALLER pause
