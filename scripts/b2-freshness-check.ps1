#Requires -Version 5.1
<#
.SYNOPSIS
    Independent B2-side freshness probe -- alerts if the latest Backblaze B2
    snapshot is older than $MaxAgeHours.

.DESCRIPTION
    The nightly backup script writes a row into the backup_jobs Postgres table
    on completion, and Argus's 08:00 cron reads that row. That covers the
    "script ran and reported its outcome" path. But it MISSES:

      * Task Scheduler silently dropped the run (no row, but Argus's "no row
        in 25 hours" check is also good for this)
      * Script started, ran restic, crashed before the DB insert (script
        thinks it failed; we still want to know the snapshot did land in B2)
      * B2-side silent corruption: a snapshot got pruned / a bucket rolled
        back / encryption-key drift. The script-side DB row would say
        "success" but the actual remote snapshot might be missing or older
        than expected.

    This script asks B2 directly: what is your most recent snapshot, and how
    old is it? If older than $MaxAgeHours, post to Slack. Intentionally
    INDEPENDENT of Argus and of backup_jobs -- different signal path, catches
    different failure modes.

    Side effects:
      - Writes D:\hermes-backups\b2-freshness.json with the probe result
        (for at-a-glance inspection / dashboard scraping).
      - Posts to Slack #biz-bridgeandbolt only when stale or on probe error.

.NOTES
    Schedule daily via Task Scheduler around 08:30 (after the backup window,
    alongside or just after Argus's check). B2 read cost: a single list-objects
    on the snapshots/ prefix -- effectively free.

.PARAMETER MaxAgeHours
    Alert threshold in hours. Default 25 (daily backup + 1h buffer).

.PARAMETER Quiet
    Suppress success Slack messages (default: success is silent anyway -- this
    is for forcing silence on all paths during dry-run tests).
#>
[CmdletBinding()]
param(
    [int]$MaxAgeHours = 25,
    [switch]$Quiet
)

$ErrorActionPreference = "Continue"

# -- Config -------------------------------------------------------------------
$ResticExe    = "D:\hermes-backups\tools\restic.exe"
$PasswordFile = "D:\hermes-backups\.restic-password"
$ResticB2Repo = "s3:https://s3.us-east-005.backblazeb2.com/hermes-Argus-Hindsight-Openbrain"
$B2CredFile   = Join-Path $PSScriptRoot "..\.env"
$StatusFile   = "D:\hermes-backups\b2-freshness.json"
$FallbackStatus = "$env:USERPROFILE\.hermes-data\b2-freshness.json"

function Get-SlackToken {
    if ($env:SLACK_BOT_TOKEN) { return $env:SLACK_BOT_TOKEN }
    $EnvFile = Join-Path $PSScriptRoot "..\cognee-server\.env"
    if (Test-Path $EnvFile) {
        $Line = Get-Content $EnvFile | Where-Object { $_ -match "^SLACK_BOT_TOKEN=" } | Select-Object -First 1
        if ($Line) { return $Line.Split("=", 2)[1].Trim() }
    }
    return $null
}

function Send-SlackAlert {
    param(
        [Parameter(Mandatory)][string]$Text,
        [string]$Channel = "#biz-bridgeandbolt"
    )
    if ($Quiet) { return }
    $Token = Get-SlackToken
    if (-not $Token) {
        Write-Warning "SLACK_BOT_TOKEN not found -- no Slack alert sent. Message was: $Text"
        return
    }
    $Body = (@{ channel = $Channel; text = $Text } | ConvertTo-Json -Compress)
    try {
        Invoke-RestMethod -Uri "https://slack.com/api/chat.postMessage" -Method Post `
            -ContentType "application/json; charset=utf-8" `
            -Headers @{ Authorization = "Bearer $Token" } `
            -Body $Body | Out-Null
    } catch {
        Write-Warning "Slack post failed: $($_.Exception.Message)"
    }
}

function Write-Status {
    param([Parameter(Mandatory)][hashtable]$Data)
    $json = $Data | ConvertTo-Json -Depth 5
    foreach ($path in @($StatusFile, $FallbackStatus)) {
        try {
            $dir = Split-Path -Parent $path
            if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            $json | Set-Content -Path $path -Encoding UTF8 -ErrorAction Stop
            return
        } catch {
            # try next path
        }
    }
    Write-Warning "Could not write status to $StatusFile or $FallbackStatus"
}

# -- Pre-flight --------------------------------------------------------------
$now = Get-Date
$startedAt = $now.ToUniversalTime().ToString("o")
Write-Host "[$($now.ToString('HH:mm:ss'))] B2 freshness probe starting (threshold ${MaxAgeHours}h)"

if (-not (Test-Path $ResticExe)) {
    $msg = "Restic not found at $ResticExe"
    Send-SlackAlert ":rotating_light: B2 freshness probe ERROR -- $msg"
    Write-Status @{ checked_at = $startedAt; status = "error"; error = $msg }
    Write-Warning $msg
    exit 1
}

if (-not (Test-Path $B2CredFile)) {
    $msg = "B2 credentials file not found at $B2CredFile"
    Send-SlackAlert ":rotating_light: B2 freshness probe ERROR -- $msg"
    Write-Status @{ checked_at = $startedAt; status = "error"; error = $msg }
    Write-Warning $msg
    exit 1
}

Get-Content $B2CredFile | ForEach-Object {
    if ($_ -match '^([^#=\s]+)\s*=\s*(.+)$') {
        [System.Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim(), 'Process')
    }
}
$env:RESTIC_REPOSITORY    = $ResticB2Repo
$env:RESTIC_PASSWORD_FILE = $PasswordFile

# -- Query B2 ----------------------------------------------------------------
try {
    $SnapOut = & $ResticExe snapshots --latest 1 2>&1
    if ($LASTEXITCODE -ne 0) {
        throw "restic snapshots exited $LASTEXITCODE -- $($SnapOut -join ' ')"
    }
} catch {
    $msg = $_.Exception.Message
    Send-SlackAlert ":rotating_light: B2 freshness probe CANNOT REACH B2 -- ``$msg``"
    Write-Status @{ checked_at = $startedAt; status = "error"; error = $msg }
    Write-Warning $msg
    exit 1
}

# Find the data row: 8-hex-char short ID at start of line, followed by a date
$DataRow = $SnapOut | Where-Object { $_ -match '^[0-9a-f]{8}\s+\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}' } |
           Select-Object -Last 1
if (-not $DataRow) {
    $msg = "No snapshots found on B2 (or restic output unparseable). Raw: $($SnapOut -join ' | ')"
    Send-SlackAlert ":rotating_light: B2 freshness probe FOUND NO SNAPSHOTS -- $msg"
    Write-Status @{ checked_at = $startedAt; status = "error"; error = $msg }
    Write-Warning $msg
    exit 1
}

$Cols = $DataRow -split '\s+'
$SnapId = $Cols[0]
$SnapDateStr = "$($Cols[1]) $($Cols[2])"   # "yyyy-MM-dd HH:mm:ss"
try {
    $SnapDt = [DateTime]::ParseExact($SnapDateStr, "yyyy-MM-dd HH:mm:ss", [System.Globalization.CultureInfo]::InvariantCulture)
} catch {
    $msg = "Could not parse snapshot timestamp '$SnapDateStr'"
    Send-SlackAlert ":rotating_light: B2 freshness probe PARSE ERROR -- $msg"
    Write-Status @{ checked_at = $startedAt; status = "error"; error = $msg }
    Write-Warning $msg
    exit 1
}

$AgeHours = [math]::Round(((Get-Date) - $SnapDt).TotalHours, 1)
$Status = if ($AgeHours -le $MaxAgeHours) { "fresh" } else { "stale" }

# Clear B2 creds from env
[System.Environment]::SetEnvironmentVariable('AWS_ACCESS_KEY_ID', $null, 'Process')
[System.Environment]::SetEnvironmentVariable('AWS_SECRET_ACCESS_KEY', $null, 'Process')

# -- Write status + alert if stale -------------------------------------------
Write-Status @{
    checked_at           = $startedAt
    latest_snapshot_id   = $SnapId
    latest_snapshot_time = $SnapDt.ToUniversalTime().ToString("o")
    age_hours            = $AgeHours
    threshold_hours      = $MaxAgeHours
    status               = $Status
    error                = $null
}

Write-Host "[$((Get-Date).ToString('HH:mm:ss'))] Latest B2 snapshot: $SnapId at $SnapDateStr (${AgeHours}h old). Status: $Status"

if ($Status -eq "stale") {
    $alertText = ":warning: *B2 backup is stale* -- latest snapshot is *${AgeHours}h* old (threshold ${MaxAgeHours}h).`n" +
                 "Snapshot: ``$SnapId`` at $SnapDateStr UTC.`n" +
                 "This is an *independent* check -- if Argus's backup_jobs check is also alerting, the nightly task is failing. " +
                 "If Argus is silent but this is firing, the script lied about success (or pruned its own snapshot)."
    Send-SlackAlert $alertText
    exit 1
}

exit 0
