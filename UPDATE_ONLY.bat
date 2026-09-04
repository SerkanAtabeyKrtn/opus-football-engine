@echo off
cd /d "%~dp0"
python -c "from zoneinfo import ZoneInfo; ZoneInfo('Europe/London')" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt
python app\update.py
pause
