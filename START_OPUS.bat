@echo off
cd /d "%~dp0"
where python >nul 2>&1
if errorlevel 1 (
  echo Python bulunamadi. Python 3 kurulu olmali.
  pause
  exit /b 1
)
echo OPUS verisi guncelleniyor...
python -c "import numpy; from zoneinfo import ZoneInfo; ZoneInfo('Europe/London')" >nul 2>&1
if errorlevel 1 python -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
python app\update.py
if errorlevel 1 exit /b 1
start "" http://127.0.0.1:8765/index.html
python app\server.py
