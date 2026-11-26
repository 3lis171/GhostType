@echo off
cd /d "%~dp0"
py -c "import sys, pathlib, subprocess; p=pathlib.Path(sys.executable).with_name('pythonw.exe'); subprocess.Popen([str(p),str(pathlib.Path('app.py').resolve())],cwd=str(pathlib.Path.cwd()))"
if errorlevel 1 pause
