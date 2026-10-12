@echo off
REM Build portable app and compile the bilingual Inno Setup installer.
cd /d "%~dp0"
if not exist .venv\Scripts\python.exe (
  echo Run setup.bat first to create the Python environment.
  pause
  exit /b 1
)
set "ISCC="
for /f "delims=" %%I in ('where ISCC.exe 2^>nul') do if not defined ISCC set "ISCC=%%I"
if not defined ISCC if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if not defined ISCC if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if not defined ISCC (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isinfo.php
  pause
  exit /b 1
)
if not exist installer\wizard-logo.bmp (
  echo Installer logo assets are missing. Regenerate them from the project PNG logo.
  pause
  exit /b 1
)
set "BUILD_FROM_INSTALLER=1"
call build_exe.bat
if errorlevel 1 exit /b 1
if not exist dist\installer mkdir dist\installer
"%ISCC%" installer\ASCII-Vibes-Visualizer.iss
if errorlevel 1 (
  echo.
  echo ERROR compiling the installer.
  pause
  exit /b 1
)
echo.
echo Installer created: dist\installer\ASCII-Vibes-Visualizer-Setup.exe
pause
