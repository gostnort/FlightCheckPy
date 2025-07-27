@echo off
echo ========================================
echo    HBPR UI - Quick Start
echo ========================================
echo.

:: Check if hbpr_ui.py exists
if not exist "hbpr_ui.py" (
    echo [ERROR] hbpr_ui.py not found!
    echo Please make sure you're in the correct directory.
    pause
    exit /b 1
)

echo [INFO] Starting HBPR Processing System Web UI...
echo [INFO] Opening at: http://localhost:8501
echo [INFO] Press Ctrl+C to stop the server
echo.

:: Start Streamlit directly
streamlit run hbpr_ui.py

echo.
echo [INFO] HBPR UI stopped.
pause 