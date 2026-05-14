# Hindsight auto-start script.
# Idempotent — safe to run even if already running.
# Triggers: AtLogOn + OnWake (registered by register-hindsight-task.ps1).
#
# Steps:
#   1. If port 15432 is already listening, exit (nothing to do).
#   2. Remove stale postmaster.pid if the recorded PID is no longer live.
#   3. Start the pg0 Postgres instance via pg_ctl.
#   4. Launch the Hindsight MCP server (start-hindsight.bat) in a hidden window.

$PgCtl    = "$env:USERPROFILE\.pg0\installation\18.1.0\bin\pg_ctl.exe"
$PgData   = "$env:USERPROFILE\.pg0\instances\hindsight-mcp\data"
$PgPort   = 15432
$StartBat = "$env:USERPROFILE\.hindsight\start-hindsight.bat"
$LogDir   = "$env:USERPROFILE\.hermes\logs"
$LogFile  = "$LogDir\hindsight-start.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "=== Hindsight auto-start triggered ==="

# Step 1: Already running?
$portOpen = (Get-NetTCPConnection -LocalPort $PgPort -State Listen -ErrorAction SilentlyContinue) -ne $null
if ($portOpen) {
    Write-Log "Port $PgPort already listening — nothing to do."
    exit 0
}

# Step 2: Remove stale postmaster.pid
$PidFile = "$PgData\postmaster.pid"
if (Test-Path $PidFile) {
    $storedPid = (Get-Content $PidFile -TotalCount 1).Trim()
    $liveProc  = Get-Process -Id $storedPid -ErrorAction SilentlyContinue
    if (-not $liveProc) {
        Write-Log "Removing stale postmaster.pid (PID $storedPid not running)"
        Remove-Item $PidFile -Force
    } else {
        Write-Log "postmaster.pid present and PID $storedPid is live — port not yet bound, waiting 5s..."
        Start-Sleep -Seconds 5
        $portOpen = (Get-NetTCPConnection -LocalPort $PgPort -State Listen -ErrorAction SilentlyContinue) -ne $null
        if ($portOpen) { Write-Log "Port now open — exiting."; exit 0 }
    }
}

# Step 3: Start pg0 Postgres
if (-not (Test-Path $PgCtl)) {
    Write-Log "ERROR: pg_ctl not found at $PgCtl"
    exit 1
}
Write-Log "Starting Hindsight Postgres (pg_ctl start)..."
& $PgCtl start -D $PgData -w -t 30 2>&1 | ForEach-Object { Write-Log "  pg_ctl: $_" }
if ($LASTEXITCODE -ne 0) {
    Write-Log "ERROR: pg_ctl start failed (exit $LASTEXITCODE)"
    exit 1
}
Write-Log "Postgres started on port $PgPort"

# Step 4: Launch Hindsight MCP server
if (-not (Test-Path $StartBat)) {
    Write-Log "WARNING: start-hindsight.bat not found at $StartBat — skipping MCP server start"
    exit 0
}
Write-Log "Launching Hindsight MCP server ($StartBat)..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$StartBat`"" -WindowStyle Hidden
Write-Log "Hindsight MCP server launched."
