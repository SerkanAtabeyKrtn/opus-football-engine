@echo off
cd /d "%~dp0"
python -c "import numpy; from zoneinfo import ZoneInfo; ZoneInfo('Europe/London')" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python app\update.py
pause
