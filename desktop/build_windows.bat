@echo off
rem Builds Seal into a single windows executable, the result is written to dist\Seal.exe.
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    python -m venv .venv || goto :error
)

".venv\Scripts\python.exe" -m pip install --upgrade pip || goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt pyinstaller || goto :error
".venv\Scripts\python.exe" -m pytest tests -q || goto :error
".venv\Scripts\python.exe" -m PyInstaller --noconfirm --clean Seal.spec || goto :error

echo.
echo The application was built, it is written to dist\Seal.exe
goto :eof

:error
echo The build of Seal failed.
pause
exit /b 1
