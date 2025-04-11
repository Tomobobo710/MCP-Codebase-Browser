@echo off
echo ========================================================
echo MCP Codebase Browser Setup
echo ========================================================
echo.
echo This script will:
echo  1. Create a Python virtual environment
echo  2. Install required dependencies
echo  3. Set up a Project directory for your code
echo  4. Show you the Claude Desktop configuration
echo.

REM Check if Python is installed
python --version > nul 2>&1
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Python is not installed or not in PATH.
    echo Please install Python 3.8 or higher from https://www.python.org/
    echo and ensure it's added to your PATH.
    pause
    exit /b 1
)

REM Check if the current directory contains codebase_server.py
if not exist "codebase_server.py" (
    echo [ERROR] codebase_server.py not found in the current directory.
    echo Please run this script from the same directory as codebase_server.py.
    pause
    exit /b 1
)

echo [1/4] Creating virtual environment...
if exist "mcp_env" (
    echo Virtual environment already exists. Skipping creation.
) else (
    python -m venv mcp_env
    if %ERRORLEVEL% NEQ 0 (
        echo [ERROR] Failed to create virtual environment.
        pause
        exit /b 1
    )
    echo Virtual environment created successfully.
)

echo [2/4] Installing dependencies...
call mcp_env\Scripts\activate.bat
pip install mcp pathlib glob2
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed successfully.

echo [3/4] Setting up Project directory...
REM Get the absolute path to the current directory
for %%i in (".") do set "CURRENT_DIR=%%~fi"

REM Create a Project directory in the current folder
set "PROJECT_DIR=%CURRENT_DIR%\Project"
if not exist "%PROJECT_DIR%" (
    echo Creating Project directory...
    mkdir "%PROJECT_DIR%"
    echo Project directory created at: %PROJECT_DIR%
) else (
    echo Project directory already exists at: %PROJECT_DIR%
)

echo NOTE: Put your project files and folders in the 'Project' directory.
echo      All sub-directories are indexed recursively and files over 1MB will be ignored.
echo.

echo [4/4] Claude Desktop configuration...
echo To complete setup, you need to update your Claude Desktop configuration:

echo Add the following configuration to claude_desktop_config.json (copy and paste this):
echo.
echo {
echo   "mcpServers": {
echo     "MCP_Codebase_Browser": {
echo       "command": "%CURRENT_DIR:\=\\%\\mcp_env\\Scripts\\python.exe",
echo       "args": ["%CURRENT_DIR:\=\\%\\codebase_server.py"]
echo     }
echo   }
echo }
echo.

echo ========================================================
echo Setup completed successfully! Make sure to restart Claude Desktop!
echo You should only need to run this batch file ONCE!
echo ========================================================
echo.
pause