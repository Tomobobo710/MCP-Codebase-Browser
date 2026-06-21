@echo off
setlocal enabledelayedexpansion
echo ========================================================
echo MCP Codebase Browser Setup
echo ========================================================
echo.
echo This script will:
echo  1. Create a Python virtual environment
echo  2. Install required dependencies
echo  3. Set up a Project directory for your code
echo  4. Detect OS and available shells
echo  5. Generate CLI configuration
echo  6. Show you the Claude Desktop configuration
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

echo [1/5] Creating virtual environment...
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

echo [2/5] Installing dependencies...
call mcp_env\Scripts\activate.bat
pip install mcp
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed successfully.

echo [3/5] Setting up Project directory...
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

echo [4/5] Detecting OS and available shells...

REM Detect OS (Windows is default here since we're in .bat)
set "OS_TYPE=Windows"
set "SHELL_TYPE=cmd"
set "PYTHON_PATH=%CURRENT_DIR%\mcp_env\Scripts\python.exe"
set "CLI_INVOKE_CMD=cmd /c"

REM Check for PowerShell
powershell -Command "exit" > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "HAS_POWERSHELL=true"
) else (
    set "HAS_POWERSHELL=false"
)

REM Check for Git Bash
if exist "C:\Program Files\Git\bin\bash.exe" (
    set "HAS_BASH=true"
    set "BASH_PATH=C:\Program Files\Git\bin\bash.exe"
) else if exist "C:\Program Files (x86)\Git\bin\bash.exe" (
    set "HAS_BASH=true"
    set "BASH_PATH=C:\Program Files (x86)\Git\bin\bash.exe"
) else (
    bash --version > nul 2>&1
    if %ERRORLEVEL% EQU 0 (
        set "HAS_BASH=true"
        set "BASH_PATH=bash"
    ) else (
        set "HAS_BASH=false"
    )
)

echo Detected OS: %OS_TYPE%
echo Primary Shell: %SHELL_TYPE%
if "%HAS_POWERSHELL%"=="true" echo Available: PowerShell
if "%HAS_BASH%"=="true" echo Available: Bash

echo.
echo [5/5] Generating CLI configuration...

REM Create cli_config.json
if "%HAS_BASH%"=="true" (
    (
        echo {
        echo   "os": "%OS_TYPE%",
        echo   "primary_shell": "%SHELL_TYPE%",
        echo   "available_shells": ["cmd", "powershell", "bash"],
        echo   "python_path": "%PYTHON_PATH:\\\\",
        echo   "cli_invoke_cmd": "%CLI_INVOKE_CMD%",
        echo   "bash_available": true,
        echo   "bash_path": "%BASH_PATH:\\\\",
        echo   "powershell_available": %HAS_POWERSHELL:~0,1%%HAS_POWERSHELL:~1%,
        echo   "user_instructions": "You are on Windows with Git Bash available. Prefer bash for CLI commands when possible."
        echo }
    ) > cli_config.json
) else (
    (
        echo {
        echo   "os": "%OS_TYPE%",
        echo   "primary_shell": "%SHELL_TYPE%",
        echo   "available_shells": ["cmd", "powershell"],
        echo   "python_path": "%PYTHON_PATH:\\\\",
        echo   "cli_invoke_cmd": "%CLI_INVOKE_CMD%",
        echo   "bash_available": false,
        echo   "powershell_available": %HAS_POWERSHELL:~0,1%%HAS_POWERSHELL:~1%,
        echo   "user_instructions": "You are on Windows. Use cmd or PowerShell for CLI commands."
        echo }
    ) > cli_config.json
)

echo CLI configuration generated: cli_config.json
echo.

echo ========================================================
echo Claude Desktop configuration...
echo ========================================================
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
echo Setup completed successfully!
echo ========================================================
echo  - Virtual environment: mcp_env
echo  - Project directory: %PROJECT_DIR%
echo  - CLI config file: cli_config.json
echo  - Remember to restart Claude Desktop!
echo ========================================================
echo.
pause
