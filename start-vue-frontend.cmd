@echo off
cd /d "%~dp0frontend"

echo Starting AI Interview Vue3 frontend...
echo.
echo Vue3 frontend:
echo http://127.0.0.1:5173/vue/app/interview
echo.
echo Backend API should be running at:
echo http://127.0.0.1:8000
echo.
echo If dependencies are missing, run:
echo npm.cmd install
echo.

npm.cmd run dev

echo.
echo Vue3 frontend server stopped. Press any key to close this window.
pause >nul
