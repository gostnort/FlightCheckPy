@echo off
echo ========================================
echo    HBPR Processing System - Web UI
echo       (Organized UI Structure)
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
echo [INFO] Checking for virtual environment...

:: Check if virtual environment exists
if not exist ".venv" (
    echo [INFO] Virtual environment not found. Creating one...
    python -m venv .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create virtual environment!
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created successfully!
)

:: Activate virtual environment
echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] Failed to activate virtual environment!
    pause
    exit /b 1
)

echo [SUCCESS] Virtual environment activated!
echo [INFO] Python in virtual environment: 
python --version

echo.
echo [INFO] Installing required packages...
pip install -r requirements.txt --quiet --disable-pip-version-check

if errorlevel 1 (
    echo [ERROR] Failed to install packages!
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)

echo [SUCCESS] All packages installed successfully!
echo.

:: Check if ui/main.py exists (new organized structure)
if not exist "ui\main.py" (
    echo [ERROR] ui/main.py not found!
    echo Please make sure you're running this script from the correct directory.
    echo The new UI structure requires ui/main.py to be present.
    pause
    exit /b 1
)

echo [INFO] Starting HBPR Processing System Web UI...
echo [INFO] 
echo [INFO] ====================================================
echo [INFO] Server starting with LAN access enabled...
echo [INFO] ====================================================
echo [INFO] 
echo [INFO] Open your browser and navigate to:
echo [INFO]   - Local access: http://localhost:8501
echo [INFO]   - LAN access: http://[YOUR-IP]:8501
echo [INFO] 
echo [INFO] To find your IP for LAN access: ipconfig
echo [INFO] Look for "IPv4 Address" under your network adapter
echo [INFO] 
echo [WARNING] LAN access enabled - ensure your network is secure!
echo [INFO] Press Ctrl+C in this window to stop the server
echo.

:: Start Streamlit with LAN access enabled (run from project root)
set PYTHONPATH=%CD%
streamlit run ui/main.py --server.address 0.0.0.0 --server.port 8501 --browser.serverAddress localhost --server.headless false

echo.
echo [INFO] HBPR UI has been stopped.
echo [INFO] Deactivating virtual environment...
deactivate
pause 