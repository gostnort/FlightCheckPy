@echo off
cd /d "%~dp0"

echo ========================================
echo    FlightCheckPy - Web UI
echo       (Organized UI Structure)
echo ========================================
echo.

where uv >nul 2>&1
if errorlevel 1 (
    echo [ERROR] uv is not installed or not in PATH.
    echo Install uv, then run this script again:
    echo   https://docs.astral.sh/uv/getting-started/installation/
    pause
    exit /b 1
)

echo [INFO] uv found:
uv --version

echo.
if not exist ".venv\Scripts\python.exe" (
    echo [INFO] Virtual environment not found. Creating it with uv...
    uv venv --python 3.12 .venv
    if errorlevel 1 (
        echo [ERROR] Failed to create the virtual environment.
        pause
        exit /b 1
    )
    echo [SUCCESS] Virtual environment created.
) else (
    echo [INFO] Using existing virtual environment: .venv
)

echo.
echo [INFO] Installing requirements with uv...
uv pip install -r requirements.txt --python .venv
if errorlevel 1 (
    echo [ERROR] Failed to install packages.
    echo Check the network connection and try again.
    pause
    exit /b 1
)

echo [SUCCESS] Packages are installed.
echo.

if not exist "ui\main.py" (
    echo [ERROR] ui\main.py was not found.
    echo Run this script from the FlightCheckPy directory.
    pause
    exit /b 1
)

echo [INFO] Starting FlightCheckPy...
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

set PYTHONPATH=%CD%
uv run --no-project --python .venv streamlit run ui/main.py --server.address 0.0.0.0 --server.port 8501 --browser.serverAddress localhost --server.headless false

echo.
echo [INFO] FlightCheckPy has been stopped.
echo [INFO] Database servers remain active - use server controls in login page
pause
