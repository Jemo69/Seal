@echo off
rem Starts Seal from the sources, the dependencies are installed into a virtual environment.
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :error
    .venv\Scripts\python.exe -m pip install --upgrade pip || goto :error
    .venv\Scripts\python.exe -m pip install -r requirements.txt || goto :error
)
".venv\Scripts\python.exe" -m seal
goto :eof
:error
echo The setup of Seal failed, please install python and try again.
pause
