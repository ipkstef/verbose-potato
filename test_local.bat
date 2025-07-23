@echo off
echo 🧪 TCG Pricing Calculator - Local Test
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ Python is not installed or not in PATH
    echo Please install Python from https://python.org
    pause
    exit /b 1
)

REM Install dependencies
echo 📦 Installing dependencies...
pip install -r requirements.txt

REM Run the test script
echo 🚀 Starting local test...
python test_local.py

pause 