@echo off
cd /d "%~dp0"

echo Starting AI Interview FastAPI backend...
echo.
echo Backend API docs:
echo http://127.0.0.1:8000/docs
echo.
echo Health check:
echo http://127.0.0.1:8000/api/health
echo.
echo Vue3 frontend is not served from this backend dev port.
echo To open the current main frontend, run start-vue-frontend.cmd
echo then visit:
echo http://127.0.0.1:5173/vue/app/interview
echo.

python -m uvicorn backend_python.main:app --host 127.0.0.1 --port 8000 --reload

echo.
echo Backend server stopped. Press any key to close this window.
pause >nul
