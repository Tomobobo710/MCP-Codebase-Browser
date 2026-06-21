@echo off

REM Read config from .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    if "%%a"=="TUNNEL_SUBDOMAIN" set TUNNEL_SUBDOMAIN=%%b
    if "%%a"=="SSE_PORT" set SSE_PORT=%%b
)

if "%TUNNEL_SUBDOMAIN%"=="" (
    echo [ERROR] TUNNEL_SUBDOMAIN not set in .env
    pause
    exit /b 1
)

if "%SSE_PORT%"=="" set SSE_PORT=9051

echo Starting MCP server on port %SSE_PORT%...
echo Starting tunnel at %TUNNEL_SUBDOMAIN%.serveo.net...

start "MCP Server" cmd /k python codebase_server_sse.py
start "SSH Tunnel" cmd /k ssh -4 -R %TUNNEL_SUBDOMAIN%:80:localhost:%SSE_PORT% serveo.net
