@echo off
cd /d "%~dp0"

echo Starting Python FastAPI backend...
echo.
echo If startup fails because a package is missing, run:
echo python -m pip install -r requirements.txt
echo.

python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Server stopped. Press any key to close this window.
pause >nul
