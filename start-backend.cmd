@echo off
setlocal
set "ARES_PROJECT=%~dp0"
if not exist "%ARES_PROJECT%.venv\Scripts\python.exe" (
  echo Create the project .venv and install ground_station\requirements.txt first.
  echo See ground_station\README.md.
  exit /b 1
)
pushd "%ARES_PROJECT%ground_station"
"%ARES_PROJECT%.venv\Scripts\python.exe" -m uvicorn ares.api:app --host 127.0.0.1 --port 8000 --workers 1
set "ARES_EXIT=%errorlevel%"
popd
exit /b %ARES_EXIT%
