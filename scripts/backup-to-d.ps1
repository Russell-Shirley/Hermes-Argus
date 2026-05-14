#Requires -Version 5.1
<#
.SYNOPSIS
    Nightly backup of Hermes-Argus stack to D:\hermes-backups

.DESCRIPTION
    Steps (each is independent -- a failure in one does not abort the others):
      1. pg_dumpall from argus-openbrain container  -> D:\hermes-backups\postgres\
      2. docker save hermes-argus-cognee-server:latest -> D:\hermes-backups\images\
      3. docker save postgres:17                       -> D:\hermes-backups\images\
      4. Restic snapshot of ~/.hermes-data bind mounts -> D:\hermes-backups\restic-repo\
      5. pg_dumpall from Hindsight standalone PG       -> D:\hermes-backups\postgres\

    After all steps:
      - Writes D:\hermes-backups\last-status.json
      - Inserts a row into backup_jobs PostgreSQL table
      - Posts Slack alert on failure if SLACK_BOT_TOKEN is available

.NOTES
    Run register-backup-task.ps1 once first to download Restic and create the Task.
#>

$ErrorActionPreference = "Continue"

# -- Config -------------------------------------------------------------------
$BackupRoot        = "D:\hermes-backups"
$ResticExe         = "$BackupRoot\tools\restic.exe"
$ResticRepo        = "$BackupRoot\restic-repo"
$PasswordFile      = "$BackupRoot\.restic-password"
$PostgresDir       = "$BackupRoot\postgres"
$ImagesDir         = "$BackupRoot\images"
$StatusFile        = "$BackupRoot\last-status.json"
$HermesData        = "$env:USERPROFILE\.hermes-data"
$Timestamp         = Get-Date -Format "yyyy-MM-dd_HH-mm"
$DateStamp         = Get-Date -Format "yyyy-MM-dd"
$HindsightPgDump   = "$env:USERPROFILE\.pg0\installation\18.1.0\bin\pg_dumpall.exe"
$HindsightPort     = 15432
$HindsightUser     = "hindsight"

# -- Result tracker -----------------------------------------------------------
$Result = [ordered]@{
    started_at   = (Get-Date).ToUniversalTime().ToString("o")
    completed_at = $null
    overall      = "success"
    error        = $null
    steps        = [ordered]@{
        postgres           = @{ status = "pending"; size_bytes = 0; error = $null }
        cognee_image       = @{ status = "pending"; size_bytes = 0; error = $null }
        postgres_image     = @{ status = "pending"; size_bytes = 0; error = $null }
        restic             = @{ status = "pending"; snapshot_id = $null; size_bytes = 0; error = $null }
        hindsight_postgres = @{ status = "pending"; size_bytes = 0; error = $null }
    }
}

function Write-Step {
    param([string]$Msg)
    Write-Host "[$(Get-Date -Format 'HH:mm:ss')] $Msg"
}

function Set-StepFailed {
    param([string]$Step, [string]$Msg)
    $Result.steps[$Step].status = "failed"
    $Result.steps[$Step].error  = $Msg
    $Result.overall = "failed"
    if (-not $Result.error) { $Result.error = "[$Step] $Msg" }
    Write-Warning "STEP FAILED ($Step): $Msg"
}

# -- Pre-flight ---------------------------------------------------------------
Write-Step "=== Hermes-Argus nightly backup starting ==="

if (-not (Test-Path "D:\")) {
    $Result.overall      = "failed"
    $Result.error        = "D: drive not present -- backup aborted"
    $Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    $FallbackStatus      = "$HermesData\last-backup-status.json"
    $Result | ConvertTo-Json -Depth 5 | Set-Content -Path $FallbackStatus -Encoding UTF8
    Write-Warning $Result.error
    exit 1
}

# Check Docker is reachable
$DockerOk = $false
try {
    docker info 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) { $DockerOk = $true }
} catch {}
if (-not $DockerOk) {
    Write-Warning "Docker not reachable -- image and DB backup steps will fail"
}

New-Item -ItemType Directory -Force -Path $PostgresDir | Out-Null
New-Item -ItemType Directory -Force -Path $ImagesDir   | Out-Null

if (-not (Test-Path $ResticExe)) {
    Write-Warning "Restic not found at $ResticExe -- run register-backup-task.ps1 first. Skipping Restic step."
}

$env:RESTIC_REPOSITORY    = $ResticRepo
$env:RESTIC_PASSWORD_FILE = $PasswordFile

# -- Step 1: PostgreSQL dump --------------------------------------------------
Write-Step "Step 1/5 -- pg_dumpall (argus-openbrain)"
$DumpFile = "$PostgresDir\openbrain_$Timestamp.sql"
try {
    $ContainerRunning = docker inspect -f "{{.State.Running}}" argus-openbrain 2>&1
    if ($ContainerRunning -ne "true") {
        throw "Container argus-openbrain is not running (state: $ContainerRunning)"
    }

    docker exec argus-openbrain pg_dumpall -U postgres -f /tmp/hermes_dump.sql
    if ($LASTEXITCODE -ne 0) { throw "pg_dumpall exited $($LASTEXITCODE)" }

    docker cp "argus-openbrain:/tmp/hermes_dump.sql" $DumpFile
    if ($LASTEXITCODE -ne 0) { throw "docker cp exited $($LASTEXITCODE)" }

    docker exec argus-openbrain rm -f /tmp/hermes_dump.sql

    $DumpSize = (Get-Item $DumpFile).Length
    if ($DumpSize -lt 1024) { throw "Dump suspiciously small ($DumpSize bytes) -- possible empty dump" }

    $Result.steps.postgres.status     = "success"
    $Result.steps.postgres.size_bytes = $DumpSize
    Write-Step "  OK -- $([math]::Round($DumpSize / 1MB, 1)) MB -> $DumpFile"
} catch {
    Set-StepFailed "postgres" $_.Exception.Message
}

# Prune postgres dumps older than 7 days
Get-ChildItem "$PostgresDir\openbrain_*.sql" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
    Remove-Item -Force

# -- Step 2: Docker image -- cognee-server ------------------------------------
Write-Step "Step 2/5 -- docker save cognee-server"
$CogneeImageFile = "$ImagesDir\cognee-server_$DateStamp.tar"
try {
    if (Test-Path $CogneeImageFile) {
        Write-Step "  Already saved today -- skipping"
        $Result.steps.cognee_image.status     = "success"
        $Result.steps.cognee_image.size_bytes = (Get-Item $CogneeImageFile).Length
    } else {
        docker save -o $CogneeImageFile hermes-argus-cognee-server:latest
        if ($LASTEXITCODE -ne 0) { throw "docker save exited $($LASTEXITCODE)" }
        $ImgSize = (Get-Item $CogneeImageFile).Length
        if ($ImgSize -lt 1MB) { throw "Saved image suspiciously small ($ImgSize bytes)" }
        $Result.steps.cognee_image.status     = "success"
        $Result.steps.cognee_image.size_bytes = $ImgSize
        Write-Step "  OK -- $([math]::Round($ImgSize / 1GB, 2)) GB -> $CogneeImageFile"
    }
} catch {
    Set-StepFailed "cognee_image" $_.Exception.Message
}
Get-ChildItem "$ImagesDir\cognee-server_*.tar" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 | Remove-Item -Force

# -- Step 3: Docker image -- postgres:17 --------------------------------------
Write-Step "Step 3/5 -- docker save postgres:17"
$PgImageFile = "$ImagesDir\postgres-17_$DateStamp.tar"
try {
    if (Test-Path $PgImageFile) {
        Write-Step "  Already saved today -- skipping"
        $Result.steps.postgres_image.status     = "success"
        $Result.steps.postgres_image.size_bytes = (Get-Item $PgImageFile).Length
    } else {
        docker save -o $PgImageFile postgres:17
        if ($LASTEXITCODE -ne 0) { throw "docker save exited $($LASTEXITCODE)" }
        $PgImgSize = (Get-Item $PgImageFile).Length
        $Result.steps.postgres_image.status     = "success"
        $Result.steps.postgres_image.size_bytes = $PgImgSize
        Write-Step "  OK -- $([math]::Round($PgImgSize / 1GB, 2)) GB -> $PgImageFile"
    }
} catch {
    Set-StepFailed "postgres_image" $_.Exception.Message
}
Get-ChildItem "$ImagesDir\postgres-17_*.tar" -ErrorAction SilentlyContinue |
    Sort-Object LastWriteTime -Descending | Select-Object -Skip 3 | Remove-Item -Force

# -- Step 4: Restic snapshot of ~/.hermes-data --------------------------------
Write-Step "Step 4/5 -- Restic snapshot of ~/.hermes-data"
if (Test-Path $ResticExe) {
    try {
        $ResticOut = & $ResticExe backup $HermesData --tag hermes-argus --json 2>&1
        if ($LASTEXITCODE -ne 0) { throw "restic backup exited $($LASTEXITCODE) -- $($ResticOut -join ' ')" }

        $SummaryLine = $ResticOut |
            Where-Object { $_ -match '"message_type"\s*:\s*"summary"' } |
            Select-Object -Last 1
        if ($SummaryLine) {
            try {
                $Snap = $SummaryLine | ConvertFrom-Json
                $Result.steps.restic.snapshot_id = $Snap.snapshot_id
                $Result.steps.restic.size_bytes  = $Snap.total_bytes_processed
            } catch {}
        }
        $Result.steps.restic.status = "success"
        Write-Step "  OK -- snapshot $($Result.steps.restic.snapshot_id)"

        & $ResticExe forget --keep-daily 7 --keep-weekly 4 --keep-monthly 3 --prune --quiet
    } catch {
        Set-StepFailed "restic" $_.Exception.Message
    }
} else {
    $Result.steps.restic.status = "skipped"
    $Result.steps.restic.error  = "restic.exe not found -- run register-backup-task.ps1"
    Write-Warning "  Restic skipped"
}

# -- Step 5: Hindsight standalone PostgreSQL dump -----------------------------
Write-Step "Step 5/5 -- pg_dumpall (Hindsight standalone PG on port $HindsightPort)"
$HindsightDumpFile = "$PostgresDir\hindsight_$Timestamp.sql"
if (-not (Test-Path $HindsightPgDump)) {
    $Result.steps.hindsight_postgres.status = "skipped"
    $Result.steps.hindsight_postgres.error  = "pg_dumpall.exe not found at $HindsightPgDump"
    Write-Warning "  Hindsight pg_dumpall skipped -- binary not found"
} else {
    $HindsightRunning = Test-NetConnection -ComputerName localhost -Port $HindsightPort -InformationLevel Quiet -WarningAction SilentlyContinue 2>$null
    if (-not $HindsightRunning) {
        $Result.steps.hindsight_postgres.status = "skipped"
        $Result.steps.hindsight_postgres.error  = "Hindsight not running (port $HindsightPort not listening)"
        Write-Warning "  Hindsight not running on port $HindsightPort -- skipped (start Hindsight and re-run to capture)"
    } else {
        try {
            $env:PGPASSWORD = "hindsight"
            & $HindsightPgDump -h localhost -p $HindsightPort -U $HindsightUser -f $HindsightDumpFile
            $PgExit = $LASTEXITCODE
            $env:PGPASSWORD = $null
            if ($PgExit -ne 0) { throw "pg_dumpall exited $PgExit" }

            $HindsightDumpSize = (Get-Item $HindsightDumpFile).Length
            if ($HindsightDumpSize -lt 512) { throw "Dump suspiciously small ($HindsightDumpSize bytes) -- possible empty dump" }

            $Result.steps.hindsight_postgres.status     = "success"
            $Result.steps.hindsight_postgres.size_bytes = $HindsightDumpSize
            Write-Step "  OK -- $([math]::Round($HindsightDumpSize / 1MB, 2)) MB -> $HindsightDumpFile"
        } catch {
            $env:PGPASSWORD = $null
            Set-StepFailed "hindsight_postgres" $_.Exception.Message
        }
    }
}

# Prune Hindsight dumps older than 7 days
Get-ChildItem "$PostgresDir\hindsight_*.sql" -ErrorAction SilentlyContinue |
    Where-Object { $_.LastWriteTime -lt (Get-Date).AddDays(-7) } |
    Remove-Item -Force

# -- Finalize status ----------------------------------------------------------
$Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")

$StartedDt   = [DateTimeOffset]::Parse($Result.started_at)
$CompletedDt = [DateTimeOffset]::Parse($Result.completed_at)
$DurationSec = [int]($CompletedDt - $StartedDt).TotalSeconds

$StatusJson = $Result | ConvertTo-Json -Depth 5
$StatusJson | Set-Content -Path $StatusFile -Encoding UTF8
Write-Step "Status written to $StatusFile"

# -- Record to backup_jobs ----------------------------------------------------
Write-Step "Recording to backup_jobs table"
$OverallStatus = $Result.overall
$ErrMsg        = if ($Result.error) { $Result.error.Replace("'", "''") } else { "" }
$StartedStr    = $Result.started_at
$CompletedStr  = $Result.completed_at

$InsertSql  = "INSERT INTO backup_jobs"
$InsertSql += " (tool_name, job_name, target, status, duration_sec, error_message, started_at, completed_at)"
$InsertSql += " VALUES ('restic+docker', 'nightly-backup', 'D:\hermes-backups',"
$InsertSql += " '$OverallStatus', $DurationSec, NULLIF('$ErrMsg',''),"
$InsertSql += " '$StartedStr'::timestamptz, '$CompletedStr'::timestamptz);"

try {
    docker exec argus-openbrain psql -U postgres -d openbrain -c $InsertSql 2>&1 | Out-Null
    Write-Step "  DB record inserted"
} catch {
    Write-Warning "Could not write to backup_jobs: $($_.Exception.Message)"
}

# -- Slack alert on failure ---------------------------------------------------
if ($Result.overall -eq "failed") {
    Write-Step "Backup FAILED -- attempting Slack alert"

    $Token = $env:SLACK_BOT_TOKEN
    if (-not $Token) {
        $EnvFile = Join-Path $PSScriptRoot "..\cognee-server\.env"
        if (Test-Path $EnvFile) {
            $Line = Get-Content $EnvFile |
                Where-Object { $_ -match "^SLACK_BOT_TOKEN=" } |
                Select-Object -First 1
            if ($Line) { $Token = $Line.Split("=", 2)[1].Trim() }
        }
    }

    if ($Token) {
        $FailedSteps = (
            $Result.steps.GetEnumerator() |
            Where-Object { $_.Value.status -eq "failed" } |
            ForEach-Object { $_.Key }
        ) -join ", "
        $AlertText = ":rotating_light: *Hermes backup FAILED* at $(Get-Date -Format 'yyyy-MM-dd HH:mm')`nFailed steps: $FailedSteps`nError: ``$($Result.error)``"
        $AlertBody = (@{ channel = "#biz-bridgeandbolt"; text = $AlertText } | ConvertTo-Json -Compress)

        try {
            Invoke-RestMethod `
                -Uri "https://slack.com/api/chat.postMessage" `
                -Method Post `
                -ContentType "application/json; charset=utf-8" `
                -Headers @{ Authorization = "Bearer $Token" } `
                -Body $AlertBody | Out-Null
            Write-Step "  Slack alert sent to #biz-bridgeandbolt"
        } catch {
            Write-Warning "Slack alert failed: $($_.Exception.Message) -- Argus cron will surface this"
        }
    } else {
        Write-Warning "SLACK_BOT_TOKEN not found -- Argus backup_health_check cron will surface this"
    }

    Write-Step "=== Backup completed with FAILURES (exit 1) ==="
    exit 1
}

Write-Step "=== Backup completed successfully in ${DurationSec}s ==="
