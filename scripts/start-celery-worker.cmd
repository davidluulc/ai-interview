@echo off
setlocal
cd /d "%~dp0\.."
echo Starting Celery worker for AI Interview System...
echo.
echo Required environment:
echo   CELERY_TASK_ALWAYS_EAGER=false
echo   CELERY_BROKER_URL=redis://localhost:6379/1
echo   CELERY_RESULT_BACKEND=redis://localhost:6379/2
echo.
celery -A backend_python.celery_app.celery_app worker --loglevel=info --pool=solo
endlocal
