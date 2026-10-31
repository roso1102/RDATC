@echo off
setlocal
if not exist "%~dp0.venv\Scripts\python.exe" (
  echo Project .venv is missing. See ground_station\README.md.
  exit /b 1
)
pushd "%~dp0ground_station"
"%~dp0.venv\Scripts\python.exe" -m pytest tests -q
set "ARES_EXIT=%errorlevel%"
popd
exit /b %ARES_EXIT%
