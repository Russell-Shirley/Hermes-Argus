# Hindsight auto-start script.
# Idempotent — safe to run even if already running.
# Triggers: AtLogOn + OnWake (registered by register-hindsight-task.ps1).
#
# Steps:
#   1. If the Hindsight MCP API (port 8888) is already listening, exit (nothing to do).
#   2. If Postgres (port 15432) is not listening, remove stale postmaster.pid and start pg_ctl.
#   3. Launch the Hindsight MCP server (start-hindsight.bat) in a hidden window.
#
# Note: pg0 Postgres on 15432 and the MCP HTTP server on 8888 are independent.
# Both must be running for Hindsight to capture/recall. The script idempotently
# brings each up if missing — never short-circuits just because PG is up.

$PgCtl    = "$env:USERPROFILE\.pg0\installation\18.1.0\bin\pg_ctl.exe"
$PgData   = "$env:USERPROFILE\.pg0\instances\hindsight-mcp\data"
$PgPort   = 15432
$ApiPort  = 8888
$StartBat = "$env:USERPROFILE\.hindsight\start-hindsight.bat"
$LogDir   = "$env:USERPROFILE\.hermes\logs"
$LogFile  = "$LogDir\hindsight-start.log"
$PgLog    = "$LogDir\hindsight-postgres.log"

New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Write-Log {
    param([string]$Msg)
    $line = "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] $Msg"
    Write-Host $line
    Add-Content -Path $LogFile -Value $line -Encoding UTF8
}

Write-Log "=== Hindsight auto-start triggered ==="

# Step 1: Is the MCP API server already up? If so, full stack is healthy — exit.
$apiOpen = (Get-NetTCPConnection -LocalPort $ApiPort -State Listen -ErrorAction SilentlyContinue) -ne $null
if ($apiOpen) {
    Write-Log "MCP API on $ApiPort already listening — Hindsight is up, nothing to do."
    exit 0
}

# Step 2: Is Postgres already up? If so, skip pg_ctl; otherwise, start it.
$pgOpen = (Get-NetTCPConnection -LocalPort $PgPort -State Listen -ErrorAction SilentlyContinue) -ne $null
if ($pgOpen) {
    Write-Log "Postgres on $PgPort already listening — skipping pg_ctl start."
    $skipPgStart = $true
} else {
    $skipPgStart = $false
    # Remove stale postmaster.pid if present
    $PidFile = "$PgData\postmaster.pid"
    if (Test-Path $PidFile) {
        $storedPid = (Get-Content $PidFile -TotalCount 1).Trim()
        $liveProc  = Get-Process -Id $storedPid -ErrorAction SilentlyContinue
        if (-not $liveProc) {
            Write-Log "Removing stale postmaster.pid (PID $storedPid not running)"
            Remove-Item $PidFile -Force
        }
    }
}

# Step 3: Start pg0 Postgres (only if not already running)
if (-not $skipPgStart) {
    if (-not (Test-Path $PgCtl)) {
        Write-Log "ERROR: pg_ctl not found at $PgCtl"
        exit 1
    }
    Write-Log "Starting Hindsight Postgres (pg_ctl start, non-blocking)..."
    # On Windows, pg_ctl spawns a detached postmaster that inherits stdio handles.
    # Anything that waits on the parent (pipes, Start-Process -Wait) blocks indefinitely
    # even with -l set. Workaround: launch fire-and-forget via cmd /c start /B, then
    # poll the port ourselves. pg_ctl writes its own stdout to a separate log file.
    $PgCtlOut = "$LogDir\hindsight-pgctl.out.log"
    "" | Set-Content -Path $PgCtlOut -Encoding ASCII
    $cmdArgs = "/c start /B `"`" `"$PgCtl`" start -D `"$PgData`" -l `"$PgLog`" >> `"$PgCtlOut`" 2>&1"
    Start-Process -FilePath "cmd.exe" -ArgumentList $cmdArgs -WindowStyle Hidden | Out-Null

    # Wait up to 180s for the port to bind.
    # pg0 on cold start (first run after boot) can take 2-3 minutes to initialize.
    # 60s was insufficient — pg0 would miss the window and exit 1, causing the watchdog
    # to loop. 180s gives pg0 plenty of headroom.
    $portOpen = $false
    for ($i = 0; $i -lt 180; $i++) {
        if (Get-NetTCPConnection -LocalPort $PgPort -State Listen -ErrorAction SilentlyContinue) {
            $portOpen = $true
            break
        }
        Start-Sleep -Seconds 1
    }
    if (-not $portOpen) {
        Write-Log "ERROR: port $PgPort never bound (see $PgCtlOut and $PgLog)"
        exit 1
    }
    Write-Log "Postgres started on port $PgPort"
}

# Step 4: Pre-warm Ollama (gemma3:4b) before launching Hindsight
# Hindsight verifies its LLM connection at startup. If Ollama's model is cold, the
# first generate request takes 2+ minutes (VRAM load), causing repeated APIConnectionError
# timeouts that delay startup by ~6 minutes. Pre-warming here ensures Ollama is ready
# before the Python daemon tries to connect, so the verify step succeeds immediately.
$OllamaPort = 11434
$OllamaUp = (Get-NetTCPConnection -LocalPort $OllamaPort -State Listen -ErrorAction SilentlyContinue) -ne $null
if ($OllamaUp) {
    Write-Log "Ollama is running — pre-warming gemma3:4b..."
    try {
        $warmBody = '{"model":"gemma3:4b","prompt":"hi","stream":false}'
        $response = Invoke-RestMethod -Uri "http://localhost:$OllamaPort/api/generate" `
            -Method Post -Body $warmBody -ContentType "application/json" -TimeoutSec 180
        Write-Log "Ollama gemma3:4b warm — model ready."
    } catch {
        Write-Log "Ollama warm-up request failed: $($_.Exception.Message) — daemon will retry on its own."
    }
} else {
    Write-Log "Ollama not running on port $OllamaPort — skipping pre-warm (daemon will handle LLM errors)."
}

# Step 5: Launch Hindsight MCP server
if (-not (Test-Path $StartBat)) {
    Write-Log "WARNING: start-hindsight.bat not found at $StartBat — skipping MCP server start"
    exit 0
}
Write-Log "Launching Hindsight MCP server ($StartBat)..."
Start-Process -FilePath "cmd.exe" -ArgumentList "/c `"$StartBat`"" -WindowStyle Hidden
Write-Log "Hindsight MCP server launched."
