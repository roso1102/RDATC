@echo off
setlocal
set "ARES_ARDUINO_CLI=%~dp0tools\arduino-cli\arduino-cli.exe"
if exist "%ARES_ARDUINO_CLI%" goto run
set "ARES_ARDUINO_CLI="
for /f "delims=" %%I in ('where arduino-cli.exe 2^>nul') do if not defined ARES_ARDUINO_CLI set "ARES_ARDUINO_CLI=%%I"
if defined ARES_ARDUINO_CLI goto run
echo Arduino CLI was not found. See docs\setup\arduino-cli.md.
exit /b 1
:run
if exist "%~dp0arduino-cli.yaml" goto localconfig
"%ARES_ARDUINO_CLI%" %*
exit /b %errorlevel%
:localconfig
"%ARES_ARDUINO_CLI%" --config-file "%~dp0arduino-cli.yaml" %*
exit /b %errorlevel%
