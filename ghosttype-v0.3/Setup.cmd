@echo off
cd /d "%~dp0"
py -m pip install -r requirements.txt
if errorlevel 1 (pause & exit /b 1)
py -c "import tkinter, pyperclip; print('GhostType dependencies ready.')"
pause
