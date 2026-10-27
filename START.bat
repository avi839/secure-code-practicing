@echo off
setlocal EnableExtensions
REM ===========================================================================
REM  SecureReflex AI - one-click launcher (backend :8000 + frontend on the first free port 3000-3010)
REM  Opens two windows; close them (or press Ctrl+C in each) to stop.
REM ===========================================================================
title SecureReflex AI launcher

set "ROOT=%~dp0"
set "BACKEND=%ROOT%backend"
set "FRONTEND=%ROOT%frontend"
set "PY=%BACKEND%\venv\Scripts\python.exe"

echo.
echo  SecureReflex AI
echo  ---------------
echo.

REM --- 1. Backend virtual environment --------------------------------------
if not exist "%PY%" (
    echo [ERROR] Backend virtual environment not found: "%PY%"
    echo.
    echo  Create it once with:
    echo    cd /d "%BACKEND%"
    echo    python -m venv venv
    echo    venv\Scripts\python.exe -m pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

"%PY%" -c "import aiosqlite" >nul 2>&1
if errorlevel 1 (
    echo [ERROR] The aiosqlite package is missing from the backend venv.
    echo.
    echo  Install it with:
    echo    "%PY%" -m pip install --no-cache-dir aiosqlite==0.20.0
    echo.
    pause
    exit /b 1
)

REM --- 2. Node / npm --------------------------------------------------------
where npm >nul 2>&1
if errorlevel 1 (
    echo [ERROR] npm was not found on PATH. Install Node.js 18+ from https://nodejs.org
    pause
    exit /b 1
)

REM --- 3. Port checks -------------------------------------------------------
netstat -ano | findstr /R /C:":8000 .*LISTENING" >nul 2>&1
if not errorlevel 1 (
    echo [WARN] Port 8000 is already in use. Another backend may be running.
    echo        Close it, or the new backend will fail to start.
    echo.
)
REM Frontend: first free port in 3000..3010 (another service, e.g. Grafana, may already own 3000)
set "FRONTEND_PORT="
for /L %%P in (3000,1,3010) do (
    if not defined FRONTEND_PORT (
        netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul 2>&1
        if errorlevel 1 set "FRONTEND_PORT=%%P"
    )
)
if not defined FRONTEND_PORT (
    echo [ERROR] Ports 3000-3010 are all in use. Free one of them and run START.bat again.
    pause
    exit /b 1
)
if not "%FRONTEND_PORT%"=="3000" (
    echo [INFO] Port 3000 is already in use by another program. The frontend will use port %FRONTEND_PORT%.
    echo.
)
set "FRONTEND_URL=http://localhost:%FRONTEND_PORT%"

REM --- 4. Backend -----------------------------------------------------------
echo [1/3] Starting backend on http://127.0.0.1:8000 ...
start "SecureReflex Backend" cmd /k "cd /d "%BACKEND%" && venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload --reload-dir app"

echo       Waiting for /api/health (up to 40 s) ...
powershell -NoProfile -ExecutionPolicy Bypass -Command "$ok=$false; for($i=0;$i -lt 40;$i++){ try { Invoke-RestMethod -Uri 'http://127.0.0.1:8000/api/health' -TimeoutSec 2 | Out-Null; $ok=$true; break } catch { Start-Sleep -Seconds 1 } }; if($ok){exit 0}else{exit 1}"
if errorlevel 1 (
    echo [WARN] Backend did not report healthy within 40 s. Check the "SecureReflex Backend" window.
    echo        Continuing with the frontend anyway.
) else (
    echo       Backend is healthy.
)

REM --- 5. Frontend ----------------------------------------------------------
if not exist "%FRONTEND%\node_modules" (
    echo [2/3] Installing frontend dependencies ^(npm ci^) ...
    pushd "%FRONTEND%"
    call npm ci
    if errorlevel 1 (
        popd
        echo [ERROR] npm ci failed. See the output above.
        pause
        exit /b 1
    )
    popd
) else (
    echo [2/3] Frontend dependencies already installed.
)

echo [3/3] Starting frontend on %FRONTEND_URL% ...
start "SecureReflex Frontend" cmd /k "cd /d "%FRONTEND%" && npm run dev -- -p %FRONTEND_PORT%"

REM Give Next.js a few seconds to compile before opening the browser
timeout /t 6 /nobreak >nul
start "" "%FRONTEND_URL%"

echo.
echo  Frontend : %FRONTEND_URL%
echo  API      : http://127.0.0.1:8000/api/health
echo  API docs : http://127.0.0.1:8000/docs
echo.
echo  Close the "SecureReflex Backend" and "SecureReflex Frontend" windows to stop.
echo.
endlocal
