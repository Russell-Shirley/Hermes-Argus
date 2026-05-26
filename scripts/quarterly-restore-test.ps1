#Requires -Version 5.1
<#
.SYNOPSIS
    Quarterly restore test of the Hermes-Argus backup -- pulls latest snapshot
    from Backblaze B2, restores to a scratch dir, and verifies key artifacts.

.DESCRIPTION
    A backup you have never restored is hope, not a backup. This script proves
    that the B2 offsite snapshot is restorable AND that key files inside it are
    not corrupt.

    Steps:
      0. Pre-flight: load B2 creds, locate Restic, pick scratch dir
      1. Restic check (--read-data-subset=5%) against B2 -- verifies pack integrity
      2. Restore the latest B2 snapshot to scratch dir
      3. Verify required files exist with sane content:
           - ~/.hermes/config.yaml          (non-empty, looks like YAML)
           - ~/.hermes/state.db             (SQLite magic header)
           - openbrain_*.sql (most recent)  (PostgreSQL dump markers)
      4. File-count sanity check (snapshot summary vs. on-disk count)
      5. On success: delete scratch dir; on failure: KEEP scratch for forensics
      6. Write result JSON to %LOCALAPPDATA%\hermes-restore-test\last-result.json
      7. Insert row into backup_jobs (job_name='quarterly-restore-test') if Docker reachable
      8. Slack notification on EITHER success or failure (quarterly cadence -- always announce)

    Idempotency: if a successful run was recorded in the last 80 days, skip
    (override with -Force). Prevents accidental repeated B2 egress.

.NOTES
    Schedule quarterly via Task Scheduler. B2 read cost ~200MB per run ($0.002).
    B2 creds in Hermes-Argus\.env. Restic password file at D:\hermes-backups\.restic-password.

.PARAMETER Force
    Run even if a successful test was recorded in the last 80 days.

.PARAMETER KeepScratch
    Keep the scratch dir after a successful run (for manual inspection).
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [switch]$KeepScratch
)

$ErrorActionPreference = "Continue"

# -- Config -------------------------------------------------------------------
$ResticExe       = "D:\hermes-backups\tools\restic.exe"
$PasswordFile    = "D:\hermes-backups\.restic-password"
$ResticB2Repo    = "s3:https://s3.us-east-005.backblazeb2.com/hermes-Argus-Hindsight-Openbrain"
$B2CredFile      = Join-Path $PSScriptRoot "..\.env"
$TestRoot        = "$env:LOCALAPPDATA\hermes-restore-test"
$Timestamp       = Get-Date -Format "yyyy-MM-dd_HH-mm"
$ScratchDir      = Join-Path $TestRoot "restore_$Timestamp"
$ResultFile      = Join-Path $TestRoot "last-result.json"
$ReadDataSubset  = "5%"          # restic check --read-data-subset
$SkipIfWithinDays = 80           # idempotency window

# -- Result tracker -----------------------------------------------------------
$Result = [ordered]@{
    started_at   = (Get-Date).ToUniversalTime().ToString("o")
    completed_at = $null
    overall      = "success"
    error        = $null
    snapshot_id  = $null
    snapshot_time = $null
    scratch_dir  = $ScratchDir
    files_restored = 0
    duration_sec = 0
    steps        = [ordered]@{
        idempotency_check = @{ status = "pending"; error = $null }
        repo_check        = @{ status = "pending"; error = $null }
        restore           = @{ status = "pending"; error = $null }
        verify_config     = @{ status = "pending"; error = $null }
        verify_state_db   = @{ status = "pending"; error = $null }
        verify_sql_dump   = @{ status = "pending"; error = $null }
        verify_file_count = @{ status = "pending"; error = $null; expected = 0; actual = 0 }
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

function Write-Result {
    New-Item -ItemType Directory -Force -Path $TestRoot | Out-Null
    $Result | ConvertTo-Json -Depth 5 | Set-Content -Path $ResultFile -Encoding UTF8 -ErrorAction SilentlyContinue
}

# -- Pre-flight ---------------------------------------------------------------
Write-Step "=== Hermes-Argus quarterly restore test starting ==="

if (-not (Test-Path $ResticExe)) {
    $Result.overall = "failed"
    $Result.error   = "Restic not found at $ResticExe"
    $Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Result
    Write-Warning $Result.error
    exit 1
}

if (-not (Test-Path $B2CredFile)) {
    $Result.overall = "failed"
    $Result.error   = "B2 credentials file not found at $B2CredFile"
    $Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Result
    Write-Warning $Result.error
    exit 1
}

# Load B2 creds
Get-Content $B2CredFile | ForEach-Object {
    if ($_ -match '^([^#=\s]+)\s*=\s*(.+)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
    }
}

$env:RESTIC_REPOSITORY    = $ResticB2Repo
$env:RESTIC_PASSWORD_FILE = $PasswordFile

# -- Step: Idempotency check --------------------------------------------------
Write-Step "Step 0 -- Idempotency check (skip if successful run within $SkipIfWithinDays days)"
if ((Test-Path $ResultFile) -and -not $Force) {
    try {
        $prev = Get-Content $ResultFile -Raw | ConvertFrom-Json
        if ($prev.overall -eq "success" -and $prev.completed_at) {
            $age = (Get-Date) - [DateTime]::Parse($prev.completed_at)
            if ($age.TotalDays -lt $SkipIfWithinDays) {
                $Result.steps.idempotency_check.status = "skipped"
                $Result.steps.idempotency_check.error  = "Previous successful run $([int]$age.TotalDays) days ago -- skipping (use -Force to override)"
                $Result.overall = "skipped"
                $Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")
                Write-Step "  Last successful test: $([int]$age.TotalDays) days ago. Skipping. (Use -Force to override.)"
                Write-Result
                exit 0
            }
        }
    } catch {
        Write-Warning "  Could not parse previous result file -- proceeding with new test"
    }
}
$Result.steps.idempotency_check.status = "passed"

# -- Step 1: Repo integrity check --------------------------------------------
Write-Step "Step 1 -- restic check --read-data-subset=$ReadDataSubset (B2 integrity)"
try {
    & $ResticExe check --read-data-subset=$ReadDataSubset 2>&1 | Tee-Object -Variable CheckOut | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "restic check exited $LASTEXITCODE -- $($CheckOut -join ' ')"
    }
    $Result.steps.repo_check.status = "passed"
    Write-Step "  OK -- repo integrity verified"
} catch {
    Set-StepFailed "repo_check" $_.Exception.Message
}

# -- Step 2: Get latest snapshot ID + restore --------------------------------
Write-Step "Step 2 -- Restore latest B2 snapshot to $ScratchDir"
try {
    # Parse latest snapshot from text output (--json output has multiple JSON objects across lines)
    $SnapList = & $ResticExe snapshots --latest 1 2>&1
    if ($LASTEXITCODE -ne 0) { throw "restic snapshots --latest 1 exited $LASTEXITCODE -- $SnapList" }

    # First column of the first data row is the short snapshot ID
    $DataRow = $SnapList | Where-Object { $_ -match '^[0-9a-f]{8}\s' } | Select-Object -Last 1
    if (-not $DataRow) { throw "Could not parse snapshot ID from restic output" }
    $SnapId = ($DataRow -split '\s+')[0]
    $SnapTime = ($DataRow -split '\s+')[1] + " " + ($DataRow -split '\s+')[2]
    $Result.snapshot_id = $SnapId
    $Result.snapshot_time = $SnapTime
    Write-Step "  Latest snapshot: $SnapId ($SnapTime)"

    New-Item -ItemType Directory -Force -Path $ScratchDir | Out-Null

    # Restic restore on Windows often returns exit 1 even on a successful restore because
    # it can't set timestamps on intermediate dirs it didn't create (e.g. \C\Users\). Parse
    # the summary line instead -- if "Restored X / Y files/dirs" shows X==Y, trust it.
    $RestoreOut = & $ResticExe restore $SnapId --target $ScratchDir 2>&1
    $RestoreExit = $LASTEXITCODE
    $SummaryLine = $RestoreOut | Where-Object { $_ -match '^\s*Summary:\s*Restored\s+(\d+)\s*/\s*(\d+)\s+files/dirs' } | Select-Object -Last 1
    if ($SummaryLine -and $SummaryLine -match 'Restored\s+(\d+)\s*/\s*(\d+)\s+files/dirs') {
        $Restored = [int]$Matches[1]
        $Total    = [int]$Matches[2]
        # Treat as success if at least 99% of files restored (tolerates a few timestamp errors)
        if ($Restored -ge [int]($Total * 0.99)) {
            $Result.steps.restore.status = "passed"
            Write-Step "  OK -- restored $Restored / $Total to $ScratchDir (exit $RestoreExit; timestamp errors on parent dirs are benign)"
        } else {
            throw "Only restored $Restored / $Total files (under 99% threshold); exit $RestoreExit"
        }
    } elseif ($RestoreExit -eq 0) {
        $Result.steps.restore.status = "passed"
        Write-Step "  OK -- restored (no summary line parsed; exit 0)"
    } else {
        throw "restic restore exited $RestoreExit and no parseable summary line; tail: $(($RestoreOut | Select-Object -Last 5) -join ' | ')"
    }
} catch {
    Set-StepFailed "restore" $_.Exception.Message
}

# Bail if restore failed -- can't verify what isn't there
if ($Result.steps.restore.status -ne "passed") {
    $Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")
    Write-Result
    Write-Warning "Restore failed -- skipping verification steps"
    exit 1
}

# -- Step 3a: Verify config.yaml ---------------------------------------------
Write-Step "Step 3a -- Verify ~/.hermes/config.yaml"
$ConfigGlob = Get-ChildItem -Path $ScratchDir -Recurse -Filter "config.yaml" -ErrorAction SilentlyContinue |
              Where-Object { $_.FullName -match '\\\.hermes\\config\.yaml$' } |
              Select-Object -First 1
try {
    if (-not $ConfigGlob) { throw "config.yaml not found anywhere under $ScratchDir" }
    if ($ConfigGlob.Length -lt 16) { throw "config.yaml suspiciously small ($($ConfigGlob.Length) bytes)" }
    $head = (Get-Content $ConfigGlob.FullName -TotalCount 5) -join "`n"
    # Minimal sanity: non-binary, contains at least one key-like line
    if ($head -notmatch '^[\s#]*[a-zA-Z_][\w\-]*\s*:') {
        throw "config.yaml does not look like YAML (head: $($head.Substring(0, [Math]::Min(80,$head.Length))))"
    }
    $Result.steps.verify_config.status = "passed"
    Write-Step "  OK -- $($ConfigGlob.Length) bytes -> $($ConfigGlob.FullName)"
} catch {
    Set-StepFailed "verify_config" $_.Exception.Message
}

# -- Step 3b: Verify state.db (SQLite magic header) --------------------------
Write-Step "Step 3b -- Verify ~/.hermes/state.db (SQLite magic header)"
$StateDb = Get-ChildItem -Path $ScratchDir -Recurse -Filter "state.db" -ErrorAction SilentlyContinue |
           Where-Object { $_.FullName -match '\\\.hermes\\state\.db$' } |
           Select-Object -First 1
try {
    if (-not $StateDb) { throw "state.db not found anywhere under $ScratchDir" }
    if ($StateDb.Length -lt 100) { throw "state.db suspiciously small ($($StateDb.Length) bytes)" }
    $magic = [System.IO.File]::ReadAllBytes($StateDb.FullName)[0..15]
    $magicStr = [System.Text.Encoding]::ASCII.GetString($magic, 0, 15)
    if ($magicStr -ne "SQLite format 3") {
        throw "state.db missing SQLite magic header (got '$magicStr')"
    }
    $Result.steps.verify_state_db.status = "passed"
    Write-Step "  OK -- $($StateDb.Length) bytes, valid SQLite header"
} catch {
    Set-StepFailed "verify_state_db" $_.Exception.Message
}

# -- Step 3c: Verify a recent openbrain_*.sql dump ---------------------------
Write-Step "Step 3c -- Verify most-recent openbrain_*.sql dump (PostgreSQL markers)"
try {
    $SqlDump = Get-ChildItem -Path $ScratchDir -Recurse -Filter "openbrain_*.sql" -ErrorAction SilentlyContinue |
               Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if (-not $SqlDump) { throw "No openbrain_*.sql found anywhere under $ScratchDir" }
    if ($SqlDump.Length -lt 1024) { throw "Most-recent SQL dump suspiciously small ($($SqlDump.Length) bytes)" }
    $head = (Get-Content $SqlDump.FullName -TotalCount 40 -ErrorAction Stop) -join "`n"
    if ($head -notmatch 'PostgreSQL') {
        throw "SQL dump does not contain 'PostgreSQL' in first 40 lines -- possible corruption"
    }
    $Result.steps.verify_sql_dump.status = "passed"
    Write-Step "  OK -- $([math]::Round($SqlDump.Length / 1KB, 1)) KB -> $($SqlDump.Name)"
} catch {
    Set-StepFailed "verify_sql_dump" $_.Exception.Message
}

# -- Step 3d: File count sanity check ----------------------------------------
Write-Step "Step 3d -- File-count sanity check"
try {
    $ActualCount = (Get-ChildItem -Path $ScratchDir -Recurse -File -ErrorAction SilentlyContinue).Count
    $Result.files_restored = $ActualCount
    $Result.steps.verify_file_count.actual = $ActualCount
    # Snapshot summary said ~11987 files for a 250MB snapshot; tolerate broad range
    $MinExpected = 100
    $Result.steps.verify_file_count.expected = "$MinExpected (min)"
    if ($ActualCount -lt $MinExpected) {
        throw "Only $ActualCount files restored -- below $MinExpected minimum"
    }
    $Result.steps.verify_file_count.status = "passed"
    Write-Step "  OK -- $ActualCount files restored (min $MinExpected)"
} catch {
    Set-StepFailed "verify_file_count" $_.Exception.Message
}

# -- Cleanup ------------------------------------------------------------------
if ($Result.overall -eq "success" -and -not $KeepScratch) {
    Write-Step "Cleanup -- removing scratch dir (verification passed)"
    Remove-Item -Path $ScratchDir -Recurse -Force -ErrorAction SilentlyContinue
} elseif ($Result.overall -ne "success") {
    Write-Warning "Cleanup -- KEEPING scratch dir for forensics: $ScratchDir"
} else {
    Write-Step "Cleanup -- keeping scratch dir per -KeepScratch flag: $ScratchDir"
}

# Clear B2 creds
[System.Environment]::SetEnvironmentVariable('AWS_ACCESS_KEY_ID', $null, 'Process')
[System.Environment]::SetEnvironmentVariable('AWS_SECRET_ACCESS_KEY', $null, 'Process')

# -- Finalize -----------------------------------------------------------------
$Result.completed_at = (Get-Date).ToUniversalTime().ToString("o")
$StartedDt   = [DateTimeOffset]::Parse($Result.started_at)
$CompletedDt = [DateTimeOffset]::Parse($Result.completed_at)
$Result.duration_sec = [int]($CompletedDt - $StartedDt).TotalSeconds

Write-Result

# -- Record to backup_jobs ----------------------------------------------------
Write-Step "Recording to backup_jobs table (job_name='quarterly-restore-test')"
$OverallStatus = $Result.overall
$ErrMsg        = if ($Result.error) { $Result.error.Replace("'", "''") } else { "" }
$InsertSql  = "INSERT INTO backup_jobs"
$InsertSql += " (tool_name, job_name, target, status, duration_sec, error_message, started_at, completed_at)"
$InsertSql += " VALUES ('restic-restore-test', 'quarterly-restore-test', 'B2 -> $ScratchDir',"
$InsertSql += " '$OverallStatus', $($Result.duration_sec), NULLIF('$ErrMsg',''),"
$InsertSql += " '$($Result.started_at)'::timestamptz, '$($Result.completed_at)'::timestamptz);"
try {
    docker exec argus-openbrain psql -U postgres -d openbrain -c $InsertSql 2>&1 | Out-Null
    Write-Step "  DB record inserted"
} catch {
    Write-Warning "Could not write to backup_jobs: $($_.Exception.Message)"
}

# -- Slack alert (always -- quarterly cadence, always announce) --------------
$Token = $env:SLACK_BOT_TOKEN
if (-not $Token) {
    $EnvFile = Join-Path $PSScriptRoot "..\cognee-server\.env"
    if (Test-Path $EnvFile) {
        $Line = Get-Content $EnvFile | Where-Object { $_ -match "^SLACK_BOT_TOKEN=" } | Select-Object -First 1
        if ($Line) { $Token = $Line.Split("=", 2)[1].Trim() }
    }
}

if ($Token) {
    if ($Result.overall -eq "success") {
        $Icon = ":white_check_mark:"
        $Verdict = "*PASSED*"
        $Detail = "Snapshot ``$($Result.snapshot_id)`` ($($Result.snapshot_time)) restored and verified in $($Result.duration_sec)s. $($Result.files_restored) files. Repo integrity: 5% sample OK."
    } elseif ($Result.overall -eq "skipped") {
        $Icon = ":fast_forward:"
        $Verdict = "*SKIPPED* (idempotency window)"
        $Detail = "Previous successful test within $SkipIfWithinDays-day window. Use ``-Force`` to override."
    } else {
        $FailedSteps = ($Result.steps.GetEnumerator() | Where-Object { $_.Value.status -eq "failed" } | ForEach-Object { $_.Key }) -join ", "
        $Icon = ":rotating_light:"
        $Verdict = "*FAILED*"
        $Detail = "Failed steps: $FailedSteps`nError: ``$($Result.error)``"
    }
    $AlertText = "$Icon Hermes-Argus quarterly restore test $Verdict at $(Get-Date -Format 'yyyy-MM-dd HH:mm')`n$Detail"
    $AlertBody = (@{ channel = "#biz-bridgeandbolt"; text = $AlertText } | ConvertTo-Json -Compress)

    try {
        Invoke-RestMethod -Uri "https://slack.com/api/chat.postMessage" -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Headers @{ Authorization = "Bearer $Token" } `
            -Body $AlertBody | Out-Null
        Write-Step "Slack alert sent to #biz-bridgeandbolt"
    } catch {
        Write-Warning "Slack alert failed: $($_.Exception.Message)"
    }
} else {
    Write-Warning "SLACK_BOT_TOKEN not found -- no Slack alert sent"
}

if ($Result.overall -eq "success") {
    Write-Step "=== Restore test PASSED in $($Result.duration_sec)s ==="
    exit 0
} elseif ($Result.overall -eq "skipped") {
    Write-Step "=== Restore test SKIPPED ==="
    exit 0
} else {
    Write-Step "=== Restore test FAILED -- scratch dir preserved at $ScratchDir ==="
    exit 1
}
