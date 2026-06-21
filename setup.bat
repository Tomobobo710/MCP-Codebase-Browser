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
echo  4. Detect available shells
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
pip install mcp starlette uvicorn anyio sse-starlette
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install dependencies.
    pause
    exit /b 1
)
echo Dependencies installed successfully.

echo [3/5] Setting up Project directory...
for %%i in (".") do set "CURRENT_DIR=%%~fi"
set "PROJECT_DIR=%CURRENT_DIR%\Project"
if not exist "%PROJECT_DIR%" (
    echo Creating Project directory...
    mkdir "%PROJECT_DIR%"
    echo Project directory created at: %PROJECT_DIR%
) else (
    echo Project directory already exists at: %PROJECT_DIR%
)
echo NOTE: Put your project files and folders in the 'Project' directory.
echo.

echo [4/5] Detecting available shells...

REM Get home directory
set "HOME_DIR=%USERPROFILE%"
set "EXAMPLE_PATH=%USERPROFILE%\Desktop"

REM Always have cmd
set "AVAILABLE_SHELLS=cmd"
set "HAS_POWERSHELL=false"

REM Check for PowerShell
powershell -Command "exit" > nul 2>&1
if %ERRORLEVEL% EQU 0 (
    set "HAS_POWERSHELL=true"
    set "AVAILABLE_SHELLS=cmd, powershell"
    echo Detected: cmd, PowerShell
) else (
    echo Detected: cmd only
)

echo.
echo [5/5] Generating CLI configuration...

REM Escape backslashes for JSON
set "HOME_DIR_JSON=%HOME_DIR:\=\\%"
set "EXAMPLE_PATH_JSON=%EXAMPLE_PATH:\=\\%"

if "%HAS_POWERSHELL%"=="true" (
    (
        echo {
        echo   "os": "Windows",
        echo   "available_shells": ["cmd", "powershell"],
        echo   "powershell_available": true,
        echo   "home_dir": "%HOME_DIR_JSON%",
        echo   "example_path": "%EXAMPLE_PATH_JSON%"
        echo }
    ) > cli_config.json
) else (
    (
        echo {
        echo   "os": "Windows",
        echo   "available_shells": ["cmd"],
        echo   "powershell_available": false,
        echo   "home_dir": "%HOME_DIR_JSON%",
        echo   "example_path": "%EXAMPLE_PATH_JSON%"
        echo }
    ) > cli_config.json
)

echo CLI configuration generated: cli_config.json
echo.

echo ========================================================
echo Claude Desktop configuration
echo ========================================================
echo Add the following to claude_desktop_config.json:
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
echo Setup complete!
echo ========================================================
echo  - Virtual environment: mcp_env
echo  - Project directory: %PROJECT_DIR%
echo  - CLI config: cli_config.json
echo  - Restart Claude Desktop after updating the config!
echo ========================================================
echo.
pause