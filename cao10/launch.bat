@echo off
cd /d "%~dp0"
if not exist build\sfx.dll (
    echo Run build.bat first.
    pause
    exit /b 1
)
if exist "%LocalAppData%\Python\pythoncore-3.11-64\python.exe" (
    "%LocalAppData%\Python\pythoncore-3.11-64\python.exe" gui\app.py
    exit /b
)
where py >nul 2>nul
if not errorlevel 1 (
    py -3 gui\app.py
    exit /b
)
python gui\app.py
