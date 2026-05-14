#Requires -Version 5.1
<#
.SYNOPSIS
    One-time init: downloads Restic, initializes the encrypted repo on D:, deploys
    the backup_jobs schema, and registers the HermesArgusBackup Task Scheduler task.

.NOTES
    Run once from an elevated (Administrator) PowerShell session.
    Re-running is safe -- all steps are idempotent.
#>

$ErrorActionPreference = "Stop"

$BackupRoot   = "D:\hermes-backups"
$ResticExe    = "$BackupRoot\tools\restic.exe"
$ResticRepo   = "$BackupRoot\restic-repo"
$PasswordFile = "$BackupRoot\.restic-password"
$TaskName     = "HermesArgusBackup"
$BackupScript = Join-Path $PSScriptRoot "backup-to-d.ps1"
$RepoRoot     = Split-Path $PSScriptRoot -Parent

function Write-Step {
    param([string]$Msg)
    Write-Host ""
    Write-Host "-- $Msg" -ForegroundColor Cyan
}

# --- Pre-flight --------------------------------------------------------------
Write-Step "Pre-flight"

if (-not (Test-Path "D:\")) {
    throw "D: drive not found. Connect the drive and re-run."
}
Write-Host "  D: drive present"

if (-not (Test-Path $BackupScript)) {
    throw "backup-to-d.ps1 not found at $BackupScript"
}

# --- Create directory structure ----------------------------------------------
Write-Step "Creating directory structure on D:"
New-Item -ItemType Directory -Force -Path "$BackupRoot\tools" | Out-Null
New-Item -ItemType Directory -Force -Path "$BackupRoot\postgres" | Out-Null
New-Item -ItemType Directory -Force -Path "$BackupRoot\images" | Out-Null
New-Item -ItemType Directory -Force -Path $ResticRepo | Out-Null
Write-Host "  $BackupRoot structure ready"

# --- Download Restic ---------------------------------------------------------
Write-Step "Restic binary"
if (Test-Path $ResticExe) {
    $ExistingVer = & $ResticExe version 2>&1 | Select-Object -First 1
    Write-Host "  Already installed: $ExistingVer"
} else {
    Write-Host "  Fetching latest release from GitHub..."
    try {
        $Release = Invoke-RestMethod "https://api.github.com/repos/restic/restic/releases/latest"
    } catch {
        throw "Could not reach GitHub API: $($_.Exception.Message). Check internet and retry."
    }

    $Asset = $Release.assets |
        Where-Object { $_.name -match "restic_.*_windows_amd64\.zip" } |
        Select-Object -First 1

    if (-not $Asset) {
        throw "No Windows AMD64 asset found in release $($Release.tag_name)."
    }

    $SizeMB = [math]::Round($Asset.size / 1MB, 1)
    Write-Host "  Downloading $($Asset.name) ($SizeMB MB)..."
    $ZipPath = "$BackupRoot\tools\_restic_download.zip"
    Invoke-WebRequest -Uri $Asset.browser_download_url -OutFile $ZipPath -UseBasicParsing
    Expand-Archive -Path $ZipPath -DestinationPath "$BackupRoot\tools\_extract" -Force
    Remove-Item $ZipPath

    $ExtractedExe = Get-ChildItem "$BackupRoot\tools\_extract\restic*.exe" | Select-Object -First 1
    if (-not $ExtractedExe) {
        throw "restic.exe not found after extraction"
    }
    Move-Item $ExtractedExe.FullName $ResticExe -Force
    Remove-Item "$BackupRoot\tools\_extract" -Recurse -Force

    $Ver = & $ResticExe version 2>&1 | Select-Object -First 1
    Write-Host "  Installed: $Ver"
}

# --- Generate Restic password ------------------------------------------------
Write-Step "Restic encryption password"
if (Test-Path $PasswordFile) {
    Write-Host "  Password file already exists at $PasswordFile"
} else {
    $Chars = (65..90) + (97..122) + (48..57) + @(33, 35, 42, 43, 45, 61, 64)
    $Pass  = -join ($Chars | Get-Random -Count 32 | ForEach-Object { [char]$_ })
    $Pass | Set-Content -Path $PasswordFile -Encoding UTF8 -NoNewline

    Write-Host ""
    Write-Host "  IMPORTANT: Restic password written to:" -ForegroundColor Yellow
    Write-Host "    $PasswordFile" -ForegroundColor Yellow
    Write-Host "  Back this file up to Bitwarden -- without it you cannot restore." -ForegroundColor Yellow
    Write-Host ""
}

# --- Initialize Restic repo --------------------------------------------------
Write-Step "Restic repository"
$env:RESTIC_REPOSITORY    = $ResticRepo
$env:RESTIC_PASSWORD_FILE = $PasswordFile

# Temporarily allow non-zero exit so restic's "repo not found" stderr doesn't terminate the script
$savedEAP = $ErrorActionPreference
$ErrorActionPreference = "Continue"
$null = & $ResticExe snapshots 2>&1
$RepoExists = ($LASTEXITCODE -eq 0)
$ErrorActionPreference = $savedEAP

if ($RepoExists) {
    Write-Host "  Repository already initialized"
} else {
    Write-Host "  Initializing at $ResticRepo..."
    & $ResticExe init
    if ($LASTEXITCODE -ne 0) {
        throw "restic init failed (exit $($LASTEXITCODE))"
    }
    Write-Host "  Repository initialized"
}

# --- Backblaze B2 credentials and repo init ----------------------------------
Write-Step "Backblaze B2 remote repository"
$ResticB2Repo = "s3:https://s3.us-east-005.backblazeb2.com/hermes-Argus-Hindsight-Openbrain"
$B2CredFile   = Join-Path $PSScriptRoot "..\.env"

if (-not (Test-Path $B2CredFile)) {
    Write-Host ""
    Write-Host "  ACTION REQUIRED: create $B2CredFile with your B2 application key:" -ForegroundColor Yellow
    Write-Host "    AWS_ACCESS_KEY_ID=<keyID>" -ForegroundColor Yellow
    Write-Host "    AWS_SECRET_ACCESS_KEY=<applicationKey>" -ForegroundColor Yellow
    Write-Host "  Then re-run this script to initialize the B2 repo." -ForegroundColor Yellow
    Write-Host ""
} else {
    Get-Content $B2CredFile | ForEach-Object {
        if ($_ -match '^([^#=\s]+)\s*=\s*(.+)$') {
            [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
        }
    }

    $env:RESTIC_REPOSITORY    = $ResticB2Repo
    $env:RESTIC_PASSWORD_FILE = $PasswordFile

    $savedEAP = $ErrorActionPreference
    $ErrorActionPreference = "Continue"
    $null = & $ResticExe snapshots 2>&1
    $B2RepoExists = ($LASTEXITCODE -eq 0)
    $ErrorActionPreference = $savedEAP

    if ($B2RepoExists) {
        Write-Host "  B2 repository already initialized"
    } else {
        Write-Host "  Initializing B2 repository at $ResticB2Repo..."
        & $ResticExe init
        if ($LASTEXITCODE -ne 0) { throw "B2 restic init failed (exit $($LASTEXITCODE))" }
        Write-Host "  B2 repository initialized"
    }

    $env:RESTIC_REPOSITORY    = $ResticRepo
    $env:RESTIC_PASSWORD_FILE = $PasswordFile
    [System.Environment]::SetEnvironmentVariable('AWS_ACCESS_KEY_ID', $null, 'Process')
    [System.Environment]::SetEnvironmentVariable('AWS_SECRET_ACCESS_KEY', $null, 'Process')
}

# --- Deploy backup_jobs schema -----------------------------------------------
Write-Step "Deploying backup_jobs table to argus-openbrain"
$ContainerRunning = docker inspect -f "{{.State.Running}}" argus-openbrain 2>&1
if ($ContainerRunning -eq "true") {
    $TmpSql = Join-Path $env:TEMP "backup_jobs_schema.sql"
    $SqlContent  = "CREATE TABLE IF NOT EXISTS backup_jobs ("
    $SqlContent += "`n  id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),"
    $SqlContent += "`n  tool_name    TEXT NOT NULL,"
    $SqlContent += "`n  job_name     TEXT NOT NULL,"
    $SqlContent += "`n  target       TEXT,"
    $SqlContent += "`n  status       TEXT NOT NULL,"
    $SqlContent += "`n  size_bytes   NUMERIC,"
    $SqlContent += "`n  duration_sec INTEGER,"
    $SqlContent += "`n  error_message TEXT,"
    $SqlContent += "`n  started_at   TIMESTAMPTZ,"
    $SqlContent += "`n  completed_at TIMESTAMPTZ,"
    $SqlContent += "`n  created_at   TIMESTAMPTZ DEFAULT NOW()"
    $SqlContent += "`n);"
    $SqlContent += "`nCREATE INDEX IF NOT EXISTS idx_backup_jobs_status ON backup_jobs(status, created_at DESC);"
    Set-Content -Path $TmpSql -Value $SqlContent -Encoding UTF8

    docker cp $TmpSql "argus-openbrain:/tmp/backup_jobs_schema.sql"
    docker exec argus-openbrain psql -U postgres -d openbrain -f /tmp/backup_jobs_schema.sql
    docker exec argus-openbrain rm -f /tmp/backup_jobs_schema.sql
    Remove-Item $TmpSql -ErrorAction SilentlyContinue

    if ($LASTEXITCODE -eq 0) {
        Write-Host "  backup_jobs table ready"
    } else {
        Write-Warning "  Schema deploy returned non-zero -- table may already exist (OK if so)"
    }
} else {
    Write-Warning "  argus-openbrain not running -- start the stack first, then re-run"
}

# --- Register Task Scheduler task --------------------------------------------
Write-Step "Windows Task Scheduler"

$Action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NonInteractive -ExecutionPolicy Bypass -File `"$BackupScript`"" `
    -WorkingDirectory $RepoRoot

$Trigger  = New-ScheduledTaskTrigger -Daily -At "02:00"

$Settings = New-ScheduledTaskSettingsSet `
    -StartWhenAvailable `
    -RunOnlyIfIdle:$false `
    -MultipleInstances IgnoreNew `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

$Principal = New-ScheduledTaskPrincipal `
    -UserId "$env:USERDOMAIN\$env:USERNAME" `
    -LogonType S4U `
    -RunLevel Highest

$ExistingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
if ($ExistingTask) {
    Set-ScheduledTask -TaskName $TaskName `
        -Action $Action -Trigger $Trigger `
        -Settings $Settings -Principal $Principal | Out-Null
    Write-Host "  Task '$TaskName' updated"
} else {
    Register-ScheduledTask -TaskName $TaskName `
        -Action $Action -Trigger $Trigger `
        -Settings $Settings -Principal $Principal `
        -Description "Nightly Hermes-Argus backup to D: (pg_dumpall + docker images + restic)" | Out-Null
    Write-Host "  Task '$TaskName' registered -- runs daily at 02:00"
}

# --- Summary -----------------------------------------------------------------
Write-Host ""
Write-Host "Hermes-Argus backup initialized" -ForegroundColor Green
Write-Host "  Schedule : daily at 02:00"
Write-Host "  Task     : $TaskName"
Write-Host "  Repo     : $ResticRepo"
Write-Host "  Password : $PasswordFile"
Write-Host ""
Write-Host "Run a test now:" -ForegroundColor Cyan
Write-Host "  Start-ScheduledTask '$TaskName'"
Write-Host "  Get-Content D:\hermes-backups\last-status.json"
Write-Host ""
Write-Host "ACTION REQUIRED: back up $PasswordFile to Bitwarden." -ForegroundColor Yellow
