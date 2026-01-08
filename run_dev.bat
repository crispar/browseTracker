@echo off
echo Starting Browser Link Tracker (Development Mode)...
echo.

REM Activate virtual environment
call .venv\Scripts\activate.bat

REM Set development mode
set LINK_TRACKER_DEV=1

REM Run the application
python src/main.py

pause