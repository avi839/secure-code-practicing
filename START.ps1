<#
.SYNOPSIS
    SecureReflex AI - one-click launcher (backend :8000 + frontend on the first free port 3000-3010).
.DESCRIPTION
    Checks the backend venv, starts the FastAPI backend and the Next.js dev server
    in their own windows, waits for /api/health and opens the browser.
    Close the two windows (or press Ctrl+C in each) to stop.
.PARAMETER BackendPort
    Backend port (default 8000).
.PARAMETER FrontendPort
    Frontend port. When omitted, the first free port in 3000..3010 is used.
.PARAMETER NoBrowser
    Do not open the browser.
#>
param(
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000,
    [switch]$NoBrowser
)

$ErrorActionPreference = 'Stop'

$root     = $PSScriptRoot
$backend  = Join-Path $root 'backend'
$frontend = Join-Path $root 'frontend'
$py       = Join-Path $backend 'venv\Scripts\python.exe'

function Test-PortInUse([int]$Port) {
    try {
        $conn = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction Stop
        return [bool]$conn
    } catch {
        return $false
    }
}

Write-Host ''
Write-Host ' SecureReflex AI' -ForegroundColor Cyan
Write-Host ' ---------------' -ForegroundColor Cyan
Write-Host ''

# --- 1. Backend virtual environment --------------------------------------------
if (-not (Test-Path -LiteralPath $py)) {
    Write-Host "[ERROR] Backend virtual environment not found: $py" -ForegroundColor Red
    Write-Host ''
    Write-Host ' Create it once with:'
    Write-Host "   cd `"$backend`""
    Write-Host '   python -m venv venv'
    Write-Host '   .\venv\Scripts\python.exe -m pip install -r requirements.txt'
    exit 1
}

& $py -c "import aiosqlite" 2>$null
if ($LASTEXITCODE -ne 0) {
    Write-Host '[ERROR] The aiosqlite package is missing from the backend venv.' -ForegroundColor Red
    Write-Host ''
    Write-Host ' Install it with:'
    Write-Host "   & `"$py`" -m pip install --no-cache-dir aiosqlite==0.20.0"
    exit 1
}

# --- 2. Node / npm ---------------------------------------------------------------
$npm = Get-Command npm.cmd -ErrorAction SilentlyContinue
if (-not $npm) { $npm = Get-Command npm -ErrorAction SilentlyContinue }
if (-not $npm) {
    Write-Host '[ERROR] npm was not found on PATH. Install Node.js 18+ from https://nodejs.org' -ForegroundColor Red
    exit 1
}

# --- 3. Port checks --------------------------------------------------------------
if (Test-PortInUse $BackendPort) {
    Write-Host "[WARN] Port $BackendPort is already in use. Another backend may be running." -ForegroundColor Yellow
    Write-Host '       Close it, or the new backend will fail to start.' -ForegroundColor Yellow
}
if ($PSBoundParameters.ContainsKey('FrontendPort')) {
    if (Test-PortInUse $FrontendPort) {
        Write-Host "[WARN] Port $FrontendPort is already in use. Close the other program first, or omit -FrontendPort to pick a free port." -ForegroundColor Yellow
    }
} else {
    # Another service (for example Grafana) may already own 3000: use the first free port in 3000..3010.
    $freePort = 3000..3010 | Where-Object { -not (Test-PortInUse $_) } | Select-Object -First 1
    if (-not $freePort) {
        Write-Host '[ERROR] Ports 3000-3010 are all in use. Free one of them or pass -FrontendPort.' -ForegroundColor Red
        exit 1
    }
    if ($freePort -ne $FrontendPort) {
        Write-Host "[INFO] Port $FrontendPort is already in use by another program. The frontend will use port $freePort." -ForegroundColor Yellow
    }
    $FrontendPort = $freePort
}

# --- 4. Backend ------------------------------------------------------------------
Write-Host "[1/3] Starting backend on http://127.0.0.1:$BackendPort ..."
$backendCmd = "Set-Location -LiteralPath '$($backend -replace "'", "''")'; " +
              "& '.\venv\Scripts\python.exe' -m uvicorn app.main:app --host 127.0.0.1 --port $BackendPort --reload --reload-dir app"
$backendProc = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $backendCmd `
    -WorkingDirectory $backend -PassThru

Write-Host '      Waiting for /api/health (up to 40 s) ...'
$healthy = $false
for ($i = 0; $i -lt 40; $i++) {
    try {
        $health = Invoke-RestMethod -Uri "http://127.0.0.1:$BackendPort/api/health" -TimeoutSec 2
        $healthy = $true
        break
    } catch {
        Start-Sleep -Seconds 1
    }
}
if ($healthy) {
    Write-Host "      Backend is $($health.status) (database: $($health.components.database.type), demo mode: $($health.demo_mode))." -ForegroundColor Green
} else {
    Write-Host '[WARN] Backend did not report healthy within 40 s. Check the backend window. Continuing.' -ForegroundColor Yellow
}

# --- 5. Frontend -----------------------------------------------------------------
if (-not (Test-Path -LiteralPath (Join-Path $frontend 'node_modules'))) {
    Write-Host '[2/3] Installing frontend dependencies (npm ci) ...'
    Push-Location -LiteralPath $frontend
    try {
        & $npm.Source ci
        if ($LASTEXITCODE -ne 0) { throw 'npm ci failed' }
    } finally {
        Pop-Location
    }
} else {
    Write-Host '[2/3] Frontend dependencies already installed.'
}

Write-Host "[3/3] Starting frontend on http://localhost:$FrontendPort ..."
$frontendCmd = "Set-Location -LiteralPath '$($frontend -replace "'", "''")'; " +
               "`$env:BACKEND_URL = 'http://127.0.0.1:$BackendPort'; npm run dev -- -p $FrontendPort"
$frontendProc = Start-Process -FilePath 'powershell.exe' `
    -ArgumentList '-NoExit', '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command', $frontendCmd `
    -WorkingDirectory $frontend -PassThru

if (-not $NoBrowser) {
    Start-Sleep -Seconds 6
    Start-Process "http://localhost:$FrontendPort"
}

Write-Host ''
Write-Host " Frontend : http://localhost:$FrontendPort"
Write-Host " API      : http://127.0.0.1:$BackendPort/api/health"
Write-Host " API docs : http://127.0.0.1:$BackendPort/docs"
Write-Host " Window PIDs: backend $($backendProc.Id), frontend $($frontendProc.Id)"
Write-Host ''
Write-Host ' Close both windows to stop.'
