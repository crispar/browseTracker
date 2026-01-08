@echo off
echo Building Browser Link Tracker...
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Install/upgrade dependencies
echo Installing dependencies...
pip install -r requirements.txt
pip install pyinstaller

REM Clean previous builds
echo Cleaning previous builds...
if exist dist rmdir /s /q dist
if exist build rmdir /s /q build

REM Build executable
echo Building executable...
pyinstaller build.spec

REM Check if build was successful
if exist dist\LinkTracker.exe (
    echo.
    echo Build successful!
    echo Executable created: dist\LinkTracker.exe
    echo.
    echo You can now run the application from: dist\LinkTracker.exe
) else (
    echo.
    echo Build failed! Please check the error messages above.
)

pause