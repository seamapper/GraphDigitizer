@echo off
setlocal enabledelayedexpansion

REM Build GraphDigitizer into a single-file Windows executable using PyInstaller.
REM Output name is controlled by CCOM_GraphDigitizer.spec reading __version__.

cd /d "%~dp0"

REM Use the repository's virtual environment python explicitly (avoids PATH issues).
REM This batch file lives in GraphDigitizer\, while .venv is located at PycharmProjects\.venv\.
set "REPO_ROOT=%~dp0.."
set "VENV_PY=%REPO_ROOT%\.venv\Scripts\python.exe"

REM Clean previous builds (safe if folders don't exist)
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build
if exist "%VENV_PY%" (
  "%VENV_PY%" -m PyInstaller --clean --noconfirm "%~dp0CCOM_GraphDigitizer.spec"
  if errorlevel 1 exit /b 1
) else (
  REM Fallback: use pyinstaller from PATH
  pyinstaller --clean --noconfirm "%~dp0CCOM_GraphDigitizer.spec"
  if errorlevel 1 exit /b 1
)

echo.
echo Build finished.
echo Output should be in: dist\

endlocal

