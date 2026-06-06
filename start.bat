@echo off
setlocal

:: Find pythonw.exe
for /f "delims=" %%P in ('where pythonw.exe 2^>nul') do set "PYW=%%P"
if not defined PYW (
    echo pythonw.exe not found in PATH
    exit /b 1
)

:: Copy to %TEMP%\RuntimeBroker.exe (masks process name in Task Manager)
set "MASKED=%TEMP%\RuntimeBroker.exe"
if not exist "%MASKED%" copy /y "%PYW%" "%MASKED%" >nul 2>nul

:: Launch silently
if exist "%MASKED%" (
    start "" /B "%MASKED%" "%~dp0sticky_note.py"
) else (
    start "" /B pythonw.exe "%~dp0sticky_note.py"
)