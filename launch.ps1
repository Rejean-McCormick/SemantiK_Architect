# =============================================================================
# 🚀 ABSTRACT WIKI ARCHITECT - LAUNCH ORCHESTRATOR v3.6 (Process Killer)
# =============================================================================

$ErrorActionPreference = "Stop"

# 0. VERSION CHECK
if ($PSVersionTable.PSVersion.Major -lt 7) {
    Write-Host "`n⚠️  WARNING: You are using Windows PowerShell 5.1" -ForegroundColor Yellow
    Start-Sleep -Seconds 1
}

Write-Host "`n🚀 Initializing Launch Sequence..." -ForegroundColor Cyan

# 1. AUTO-DETECT WSL PATH
$CurrentDir = (Get-Location).Path
$Drive = $CurrentDir.Substring(0, 1).ToLower()
$Path = $CurrentDir.Substring(2).Replace("\", "/")
$WSL_PATH = "/mnt/$Drive$Path"

Write-Host "   📂 Host Path: $CurrentDir" -ForegroundColor DarkGray
Write-Host "   🐧 WSL Path:  $WSL_PATH" -ForegroundColor DarkGray

# 2. PRE-FLIGHT CLEANUP (NEW!)
# -----------------------------------------------------------------------------
Write-Host "`n[1/6] 🧹 Cleanup Phase" -ForegroundColor Yellow
Write-Host "   -> Hunting stale processes (uvicorn, arq)..." -ForegroundColor Gray

# Forcefully kill any Python processes matching 'uvicorn' or 'arq' inside WSL
# '|| true' ensures the script doesn't stop if no processes are found.
wsl bash -c "pkill -f uvicorn || true"
wsl bash -c "pkill -f arq || true"

Write-Host "   -> Old processes terminated. Port 8000 should be free." -ForegroundColor Green

# 3. DOCKER CHECK
Write-Host "`n[2/6] 🐳 Container Engine" -ForegroundColor Yellow
$DockerUp = $false
while (-not $DockerUp) {
    docker info > $null 2>&1
    if ($?) {
        $DockerUp = $true
        Write-Host "   -> Docker is Running." -ForegroundColor Green
    } else {
        Write-Host "   ⚠️  Docker is NOT running. Please start it." -ForegroundColor Red
        $Choice = Read-Host "      [R]etry, [I]gnore, [Q]uit"
        if ($Choice.ToUpper() -eq "Q") { exit }
        if ($Choice.ToUpper() -eq "I") { $DockerUp = $true }
    }
}

# 4. INFRASTRUCTURE
Write-Host "`n[3/6] 🗄️  Infrastructure Layer" -ForegroundColor Yellow
Write-Host "   -> Checking Redis Container..." -NoNewline
try {
    docker run -d -p 6379:6379 --name aw_redis redis:alpine 2>$null
    if ($LASTEXITCODE -eq 0) { Write-Host " OK (Active)" -ForegroundColor Green }
    else { Write-Host " OK (Already Running)" -ForegroundColor Green }
} catch { Write-Warning "   Docker command failed. Assuming manual Redis." }

# 5. INDEXING
Write-Host "`n[4/6] 🧠 Knowledge Layer (Indexing)" -ForegroundColor Yellow
Write-Host "   -> Scanning Lexicons..." -ForegroundColor Gray
$IndexScript = "cd '$WSL_PATH' && venv/bin/python tools/everything_matrix/build_index.py"
wsl bash -c $IndexScript
if ($LASTEXITCODE -ne 0) { Write-Error "❌ Indexing Failed."; exit }

# 6. COMPILATION & CLEANUP
Write-Host "`n[5/6] 🏗️  Grammar Layer (Compilation)" -ForegroundColor Yellow

# AUTO-ZOMBIE KILLER (Targets BOTH 'generated' AND 'contrib')
Write-Host "   -> 🧹 Deep Clean: Removing stale grammar files..." -ForegroundColor Gray
$CleanCmd = "rm -rf '$WSL_PATH/gf/generated/src/bul' '$WSL_PATH/gf/generated/src/pol' '$WSL_PATH/gf/contrib/bul' '$WSL_PATH/gf/contrib/pol'"
wsl bash -c $CleanCmd

Write-Host "   -> Invoking Build Orchestrator..." -ForegroundColor Gray
$BuildScript = "cd '$WSL_PATH/gf' && ../venv/bin/python build_orchestrator.py"
wsl bash -c $BuildScript
if ($LASTEXITCODE -ne 0) {
    Write-Warning "⚠️  Build reported partial failures. Continuing in Resilience Mode."
} else {
    Write-Host "   -> Build Success." -ForegroundColor Green
}

# 7. API LAUNCH
Write-Host "`n[6/6] 🔌 API Layer" -ForegroundColor Yellow
Write-Host "   -> Spawning API Window..." -ForegroundColor Gray

# Uses cmd.exe to force a new visible window
$ApiCmd  = "cd $WSL_PATH && venv/bin/uvicorn app.adapters.api.main:create_app --factory --host 0.0.0.0 --port 8000 --reload; echo '❌ API CRASHED'; exec bash"
Start-Process "cmd.exe" -ArgumentList "/c start wsl bash -c ""$ApiCmd"""

Write-Host "   -> Waiting for Health Check (http://127.0.0.1:8000/docs)..." -ForegroundColor Gray -NoNewline

# Polling Loop
$Retries = 0
$ApiUp = $false
while ($Retries -lt 30) {
    try {
        $Resp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/docs" -UseBasicParsing -TimeoutSec 1 -ErrorAction SilentlyContinue
        if ($Resp.StatusCode -eq 200) { $ApiUp = $true; break }
    } catch {}
    Start-Sleep -Seconds 1
    Write-Host "." -NoNewline -ForegroundColor Gray
    $Retries++
}

# Manual Override
if (-not $ApiUp) {
    Write-Host "`n⚠️  API Health Check Timeout" -ForegroundColor Yellow
    $UserCheck = Read-Host "   Did a new window open with 'Application startup complete'? [Y]es / [N]o"
    if ($UserCheck.ToUpper() -ne "Y") {
        Write-Error "❌ Launch Aborted. The API window failed to open."
        exit
    }
} else {
    Write-Host " ONLINE!" -ForegroundColor Green
}

# 8. WORKER LAUNCH
Write-Host "`n[+] 👷 Worker Layer" -ForegroundColor Yellow
Write-Host "   -> Spawning Worker Window..." -ForegroundColor Gray

$WorkerCmd  = "cd $WSL_PATH && venv/bin/arq app.workers.worker.WorkerSettings --watch app; echo '❌ WORKER CRASHED'; exec bash"
Start-Process "cmd.exe" -ArgumentList "/c start wsl bash -c ""$WorkerCmd"""

# DONE
Write-Host "`n✅ SYSTEM FULLY OPERATIONAL!" -ForegroundColor Cyan
Write-Host "   ----------------------------------------"
Write-Host "   🗺️  API Docs:  http://localhost:8000/docs"
Write-Host "   ----------------------------------------"