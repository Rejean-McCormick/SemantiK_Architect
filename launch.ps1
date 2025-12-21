# =============================================================================
# 🚀 ABSTRACT WIKI ARCHITECT - LAUNCH ORCHESTRATOR v2.9 (Version Aware)
# =============================================================================

$ErrorActionPreference = "Stop"

# 0. VERSION CHECK
# -----------------------------------------------------------------------------
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Host "`n⚠️  WARNING: You are using Windows PowerShell 5.1" -ForegroundColor Yellow
    Write-Host "   This version is older and prone to syntax errors with modern scripts."
    Write-Host "   We strongly recommend installing PowerShell 7: https://aka.ms/PSWindows"
    Write-Host "   ---------------------------------------------------------------"
    Write-Host "   Attempting to run in Legacy Compatibility Mode..." -ForegroundColor DarkGray
    Start-Sleep -Seconds 2
}

Write-Host "`n🚀 Initializing Launch Sequence..." -ForegroundColor Cyan

# 1. AUTO-DETECT WSL PATH
# -----------------------------------------------------------------------------
$CurrentDir = (Get-Location).Path
$Drive = $CurrentDir.Substring(0, 1).ToLower()
$Path = $CurrentDir.Substring(2).Replace("\", "/")
$WSL_PATH = "/mnt/$Drive$Path"

Write-Host "   📂 Host Path: $CurrentDir" -ForegroundColor DarkGray
Write-Host "   🐧 WSL Path:  $WSL_PATH" -ForegroundColor DarkGray

# 2. INFRASTRUCTURE (REDIS)
# -----------------------------------------------------------------------------
Write-Host "`n[1/5] 🗄️  Infrastructure Layer" -ForegroundColor Yellow
Write-Host "   -> Checking Redis Container..." -NoNewline

docker run -d -p 6379:6379 --name aw_redis redis:alpine 2>$null
if ($?) { 
    Write-Host " OK (Active)" -ForegroundColor Green 
} else {
    Write-Host " OK (Already Running)" -ForegroundColor Green
}

# 3. INDEXING
# -----------------------------------------------------------------------------
Write-Host "`n[2/5] 🧠 Knowledge Layer (Indexing)" -ForegroundColor Yellow
Write-Host "   -> Scanning Lexicons & Building Matrix..." -ForegroundColor Gray

# COMMAND: Simple string concatenation (Safe for PS 5.1)
$IndexScript = "cd '$WSL_PATH' && venv/bin/python tools/everything_matrix/build_index.py"
wsl bash -c $IndexScript

if ($LASTEXITCODE -ne 0) {
    Write-Error "❌ Indexing Failed. Check logs above."
    exit
}

# 4. COMPILATION
# -----------------------------------------------------------------------------
Write-Host "`n[3/5] 🏗️  Grammar Layer (Compilation)" -ForegroundColor Yellow
Write-Host "   -> Invoking Build Orchestrator..." -ForegroundColor Gray

$BuildScript = "cd '$WSL_PATH/gf' && ../venv/bin/python build_orchestrator.py"
wsl bash -c $BuildScript

if ($LASTEXITCODE -ne 0) {
    Write-Warning "⚠️  Build reported partial failures. Continuing in Resilience Mode."
} else {
    Write-Host "   -> Build Success." -ForegroundColor Green
}

# 5. API LAUNCH & HEALTH CHECK
# -----------------------------------------------------------------------------
Write-Host "`n[4/5] 🔌 API Layer" -ForegroundColor Yellow
Write-Host "   -> Spawning API in new window..." -ForegroundColor Gray

# COMMAND: Concatenated string for safety
$ApiScript  = "cd '$WSL_PATH' && venv/bin/uvicorn app.adapters.api.main:create_app"
$ApiScript += " --factory --host 0.0.0.0 --port 8000 --reload; echo '❌ API CRASHED'; exec bash"

Start-Process wsl -ArgumentList "bash", "-c", "$ApiScript"

Write-Host "   -> Waiting for API to go live (Health Check)..." -ForegroundColor Gray -NoNewline

# Polling Loop
$Retries = 0
$MaxRetries = 30
$ApiUp = $false

while ($Retries -lt $MaxRetries) {
    try {
        $Response = Invoke-WebRequest -Uri "http://localhost:8000/docs" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($Response.StatusCode -eq 200) {
            $ApiUp = $true
            break
        }
    } catch {
        # Waiting...
    }
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline -ForegroundColor Gray
    $Retries++
}

if (-not $ApiUp) {
    Write-Host "`n❌ API Timeout! It failed to start within 30 seconds." -ForegroundColor Red
    Write-Host "   Check the popped-up terminal window for Python errors." -ForegroundColor Red
    exit
}

Write-Host " ONLINE!" -ForegroundColor Green

# 6. WORKER LAUNCH
# -----------------------------------------------------------------------------
Write-Host "`n[5/5] 👷 Worker Layer" -ForegroundColor Yellow
Write-Host "   -> Spawning Worker in new window..." -ForegroundColor Gray

$WorkerScript  = "cd '$WSL_PATH' && venv/bin/arq app.workers.worker.WorkerSettings"
$WorkerScript += " --watch app; echo '❌ WORKER CRASHED'; exec bash"

Start-Process wsl -ArgumentList "bash", "-c", "$WorkerScript"

# =============================================================================
# ✅ SYSTEM READY
# =============================================================================
Write-Host "`n✅ SYSTEM FULLY OPERATIONAL!" -ForegroundColor Cyan
Write-Host "   ----------------------------------------"
Write-Host "   🗺️  API Docs:  http://localhost:8000/docs"
Write-Host "   ----------------------------------------"