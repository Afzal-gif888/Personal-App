<#
.SYNOPSIS
    Start AgentOS: backend (8000), Agent Core (8001) and frontend (5173), each in its own window.

.EXAMPLE
    .\start.ps1                 # migrate the database, start everything, open the browser
    .\start.ps1 -SkipMigrations -NoBrowser

    Stop everything with .\stop.ps1 (or close the three windows).
#>
param(
    [switch]$SkipMigrations,
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
$pidFile = Join-Path $root ".agentos-pids"

function Test-Port([int]$Port) {
    $client = New-Object System.Net.Sockets.TcpClient
    try { $client.Connect("localhost", $Port); return $true } catch { return $false } finally { $client.Close() }
}

function Wait-Http([string]$Url, [int]$Seconds) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try {
            $r = Invoke-WebRequest -Uri $Url -UseBasicParsing -TimeoutSec 5
            if ($r.StatusCode -lt 500) { return $true }
        } catch { }
        Start-Sleep -Milliseconds 700
    }
    return $false
}

function Fail([string]$Message) {
    Write-Host "  $Message" -ForegroundColor Red
    exit 1
}

Write-Host "`nIt's Personal - starting`n" -ForegroundColor Cyan

# --- prerequisites -------------------------------------------------------------------------------
$backendPy = Join-Path $root "backend\.venv\Scripts\python.exe"
$agentPy = Join-Path $root "agent-core\.venv\Scripts\python.exe"
if (-not (Test-Path $backendPy)) { Fail "backend\.venv is missing. Run: cd backend; python -m venv .venv; .venv\Scripts\pip install -r requirements-dev.txt" }
if (-not (Test-Path $agentPy)) { Fail "agent-core\.venv is missing. Run: cd agent-core; python -m venv .venv; .venv\Scripts\pip install -r requirements-dev.txt" }
if (-not (Test-Path (Join-Path $root "backend\.env"))) { Fail "backend\.env is missing. Copy backend\.env.example and set DATABASE_URL." }
if (-not (Test-Path (Join-Path $root "agent-core\.env"))) { Fail "agent-core\.env is missing. Copy agent-core\.env.example." }
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Fail "Node.js/npm is not installed." }
if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
    Write-Host "  Installing frontend packages (first run)..." -ForegroundColor Yellow
    Push-Location (Join-Path $root "frontend"); npm ci; $ok = $?; Pop-Location
    if (-not $ok) { Fail "npm ci failed." }
}
if (-not (Test-Port 5432)) { Fail "PostgreSQL is not reachable on localhost:5432. Start it (services.msc -> postgresql) and retry." }
Write-Host "  Prerequisites OK (PostgreSQL is running)" -ForegroundColor Green

# --- database ------------------------------------------------------------------------------------
Push-Location (Join-Path $root "backend")
try {
    if (-not $SkipMigrations) {
        Write-Host "  Applying database migrations..."
        # Alembic logs to stderr; don't let PowerShell treat that as an error.
        $ErrorActionPreference = "Continue"
        & $backendPy -m alembic upgrade head 2>&1 | ForEach-Object { "    $_" }
        $code = $LASTEXITCODE
        $ErrorActionPreference = "Stop"
        if ($code -ne 0) { Fail "Migrations failed. Check DATABASE_URL in backend\.env." }
    }
} finally { Pop-Location }

# --- services ------------------------------------------------------------------------------------
$services = @(
    @{ Name = "Backend";    Port = 8000; Dir = "backend";    Health = "http://127.0.0.1:8000/health"
       Command = "& '.venv\Scripts\python.exe' -m uvicorn app.main:app --reload --port 8000 | ForEach-Object { `$_; Add-Content -Path '..\logs\backend.log' -Value `$_ -Encoding UTF8 }" },
    @{ Name = "Agent Core"; Port = 8001; Dir = "agent-core"; Health = "http://127.0.0.1:8001/health"
       Command = "& '.venv\Scripts\python.exe' -m uvicorn app.main:create_app --factory --port 8001 | ForEach-Object { `$_; Add-Content -Path '..\logs\agent-core.log' -Value `$_ -Encoding UTF8 }" },
    @{ Name = "Frontend";   Port = 5173; Dir = "frontend";   Health = "http://localhost:5173"
       Command = "npm run dev" }
)

New-Item -ItemType Directory -Force -Path (Join-Path $root "logs") | Out-Null
$started = @()
foreach ($svc in $services) {
    if (Test-Port $svc.Port) {
        Write-Host ("  {0}: port {1} already in use - assuming it is already running" -f $svc.Name, $svc.Port) -ForegroundColor Yellow
        continue
    }
    $title = "AgentOS - $($svc.Name) :$($svc.Port)"
    $script = "`$Host.UI.RawUI.WindowTitle = '$title'; $($svc.Command)"
    $proc = Start-Process powershell -PassThru -WorkingDirectory (Join-Path $root $svc.Dir) `
        -ArgumentList "-NoExit", "-ExecutionPolicy", "Bypass", "-Command", $script
    $started += $proc.Id
    Write-Host ("  {0}: starting in a new window" -f $svc.Name)
}
if ($started.Count -gt 0) { Add-Content -Path $pidFile -Value $started }

# --- health --------------------------------------------------------------------------------------
Write-Host ""
$allUp = $true
foreach ($svc in $services) {
    if (Wait-Http $svc.Health 90) {
        Write-Host ("  [ok]  {0,-11} http://localhost:{1}" -f $svc.Name, $svc.Port) -ForegroundColor Green
    } else {
        Write-Host ("  [!!]  {0,-11} did not respond - check its window for errors" -f $svc.Name) -ForegroundColor Red
        $allUp = $false
    }
}

try {
    $ready = Invoke-RestMethod -Uri "http://127.0.0.1:8001/ready" -TimeoutSec 5
    Write-Host ("`n  Assistant model provider: {0}   (backend reachable: {1})" -f $ready.checks.llm, $ready.checks.backend)
} catch { Write-Host "`n  Agent Core /ready: backend not reachable yet" -ForegroundColor Yellow }

Write-Host "`n  App:        http://localhost:5173   (create your account on the Register page)"
Write-Host "  API docs:   http://localhost:8000/docs"
Write-Host "  Agent docs: http://localhost:8001/docs"
Write-Host "  Logs:       logs\backend.log, logs\agent-core.log"
Write-Host "  Stop with:  .\stop.ps1`n"

if ($allUp -and -not $NoBrowser) { Start-Process "http://localhost:5173" }
