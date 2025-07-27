@echo off
echo ========================================
echo    HBPR Processing System - Web UI
echo ========================================
echo.

:: Check if Python is installed
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python is not installed or not in PATH!
    echo Please install Python 3.7+ and try again.
    pause
    exit /b 1
)

echo [INFO] Python found: 
python --version

echo.
echo [INFO] Installing required packages...
pip install streamlit pandas openpyxl --quiet --disable-pip-version-check

if errorlevel 1 (
    echo [ERROR] Failed to install packages!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo [SUCCESS] All packages installed successfully!
echo.

:: Check if hbpr_ui.py exists
if not exist "hbpr_ui.py" (
    echo [ERROR] hbpr_ui.py not found!
    echo Please make sure you're running this script from the correct directory.
    pause
    exit /b 1
)

echo [INFO] Starting HBPR Processing System Web UI...
echo [INFO] The application will open in your default browser at: http://localhost:8501
echo [INFO] Press Ctrl+C in this window to stop the server
echo.

:: Start Streamlit (this will automatically open the browser)
streamlit run hbpr_ui.py --server.headless false

echo.
echo [INFO] HBPR UI has been stopped.
pause 