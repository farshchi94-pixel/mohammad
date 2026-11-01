@echo off
setlocal
cd /d "%~dp0"

where py >nul 2>nul
if errorlevel 1 (
  echo Python launcher (py) was not found. Install Python 3.11+ first.
  pause
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating the local Atlas Quant environment...
  py -3 -m venv .venv
)

call ".venv\Scripts\activate.bat"
python -m pip install --disable-pip-version-check -r signal-hub\requirements.txt

echo Running the paper-only DayTraderSkill scan...
python signal-hub\scan.py --atlas
if errorlevel 1 (
  echo The scan failed. The API was not started.
  pause
  exit /b 1
)

echo Starting Atlas Quant API on http://0.0.0.0:5000
python signal-hub\atlas_api.py --host 0.0.0.0 --port 5000
