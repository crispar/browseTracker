@echo off
setlocal

echo Building Browser Link Tracker...
echo.

if not exist .venv\Scripts\python.exe (
    echo ERROR: .venv\Scripts\python.exe not found.
    echo Please create the virtual environment first.
    exit /b 1
)

set "VENV_PY=.venv\Scripts\python.exe"

REM Install/update dependencies (best-effort in offline environments)
echo Installing dependencies...
"%VENV_PY%" -m pip install -r requirements.txt
if errorlevel 1 (
    echo WARNING: Could not refresh requirements from network. Continuing with installed packages.
)

REM Validate PyInstaller availability inside .venv
"%VENV_PY%" -m PyInstaller --version >nul 2>&1
if errorlevel 1 (
    echo.
    echo Build failed: PyInstaller is not available in .venv.
    exit /b 1
)

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build executable
echo Building executable...
"%VENV_PY%" -m PyInstaller build.spec
if errorlevel 1 (
    echo.
    echo Build failed! Please check the error messages above.
    exit /b 1
)

REM Check if build was successful
if exist dist\LinkTracker.exe (
    echo.
    echo Build successful!
    echo Executable created: dist\LinkTracker.exe
    echo.
    echo You can now run the application from: dist\LinkTracker.exe
    exit /b 0
)

echo.
echo Build failed! dist\LinkTracker.exe was not generated.
exit /b 1
