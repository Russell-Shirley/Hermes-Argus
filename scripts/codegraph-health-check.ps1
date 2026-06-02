#Requires -Version 5.1
<#
.SYNOPSIS
    CodeGraph health probe -- verifies binary, MCP wiring, and repo indexes across
    all Bridge & Bolt codebases. Designed to run twice daily via Task Scheduler.

.DESCRIPTION
    Three independent checks:
    1. codegraph binary responds on PATH (npm global install still intact)
    2. MCP server entry exists in ~/.claude.json (Claude Code auto-activates it)
    3. Each registered repo has a populated .codegraph/db.sqlite (init was run)

    Writes D:\hermes-backups\codegraph-health.json after every run (healthy or not).
    Posts to Slack #biz-bridgeandbolt ONLY when status = error or warning.
    The companion Argus cron (jobs.json: codegraph_health_check) reads this file
    15 minutes later and can surface additional context.

    Register schedule with: scripts\register-codegraph-health-task.ps1
    Inspect last result:    Get-Content D:\hermes-backups\codegraph-health.json | ConvertFrom-Json | Format-List

.PARAMETER MaxStaleHours
    Emit a warning if a repo's DB has not been touched in this many hours.
    Default 72 (3 days). The file watcher only updates on actual file saves, so a
    quiet weekend is expected -- this is a soft signal, not a hard error.

.PARAMETER Quiet
    Suppress all Slack output. Useful for manual dry-run testing.
#>
[CmdletBinding()]
param(
    [int]$MaxStaleHours = 72,
    [switch]$Quiet
)

$ErrorActionPreference = "Continue"

# -- Config -------------------------------------------------------------------
$StatusFile     = "D:\hermes-backups\codegraph-health.json"
$FallbackStatus = "$env:USERPROFILE\.hermes-data\codegraph-health.json"
$ClaudeJson     = "$env:USERPROFILE\.claude.json"

$Repos = @(
    @{ name = "ai-factory";       path = "C:\Users\Russell\Documents\GitHub\ai-factory" },
    @{ name = "bridgeboard-ai";   path = "C:\Users\Russell\Documents\GitHub\bridgeboard-ai" },
    @{ name = "Bridge-and-Bolt";  path = "C:\Users\Russell\Documents\GitHub\Bridge-and-Bolt" },
    @{ name = "SessionZest";      path = "C:\Users\Russell\Documents\GitHub\SessionZest" },
    @{ name = "second-brain-app"; path = "C:\Users\Russell\Documents\GitHub\second-brain-app" },
    @{ name = "cognee-fork";      path = "C:\Users\Russell\Documents\GitHub\cognee-fork" }
)

# -- Helpers ------------------------------------------------------------------
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
    param([Parameter(Mandatory)][string]$Text, [string]$Channel = "#biz-bridgeandbolt")
    if ($Quiet) { return }
    $Token = Get-SlackToken
    if (-not $Token) {
        Write-Warning "SLACK_BOT_TOKEN not found -- Slack alert suppressed. Message was: $Text"
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
    $json = $Data | ConvertTo-Json -Depth 10
    foreach ($statusPath in @($StatusFile, $FallbackStatus)) {
        try {
            $dir = Split-Path -Parent $statusPath
            if ($dir -and -not (Test-Path $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
            $json | Set-Content -Path $statusPath -Encoding UTF8 -ErrorAction Stop
            return
        } catch { }
    }
    Write-Warning "Could not write status to $StatusFile or $FallbackStatus"
}

# -- Probe start --------------------------------------------------------------
$now       = Get-Date
$checkedAt = $now.ToUniversalTime().ToString("o")
$errors    = [System.Collections.Generic.List[string]]::new()
$warnings  = [System.Collections.Generic.List[string]]::new()
$repoResults = [System.Collections.Generic.List[object]]::new()

Write-Host "[$($now.ToString('HH:mm:ss'))] CodeGraph health probe starting"

# Check 1: binary ------------------------------------------------------------
Write-Host "  [1/3] Binary check..."
$binaryVersion = $null
try {
    $verOut = & codegraph --version 2>&1
    if ($LASTEXITCODE -ne 0) { throw "exited $LASTEXITCODE" }
    $binaryVersion = ($verOut | Select-String '\d+\.\d+\.\d+').Matches.Value | Select-Object -First 1
    Write-Host "        OK -- codegraph $binaryVersion"
} catch {
    $msg = "codegraph binary not found or crashed: $($_.Exception.Message). Reinstall: npm install -g @colbymchenry/codegraph"
    Write-Warning "        FAIL -- $msg"
    $errors.Add($msg)
}

# Check 2: MCP wiring --------------------------------------------------------
Write-Host "  [2/3] MCP wiring check (~/.claude.json)..."
$mcpWired = $false
if (-not (Test-Path $ClaudeJson)) {
    $msg = "~/.claude.json not found at $ClaudeJson -- Claude Code may not be configured"
    Write-Warning "        FAIL -- $msg"
    $errors.Add($msg)
} else {
    # Use string search rather than ConvertFrom-Json -- the file can contain duplicate
    # casing keys (e.g. two project path entries differing only by case) which causes
    # ConvertFrom-Json to throw even when the MCP entry is present and correct.
    $raw = Get-Content $ClaudeJson -Raw
    if ($raw -match '"codegraph"\s*:') {
        Write-Host "        OK -- codegraph entry present in mcpServers"
        $mcpWired = $true
    } else {
        $msg = "codegraph MCP server entry missing from ~/.claude.json. Re-run: codegraph install --yes --target=claude"
        Write-Warning "        FAIL -- $msg"
        $errors.Add($msg)
    }
}

# Check 3: repo databases ----------------------------------------------------
Write-Host "  [3/3] Repo index check ($($Repos.Count) repos)..."
foreach ($repo in $Repos) {
    $dbPath = Join-Path $repo.path ".codegraph\codegraph.db"
    $result = [ordered]@{
        repo     = $repo.name
        path     = $repo.path
        db       = $dbPath
        status   = "unknown"
        size_kb  = $null
        age_h    = $null
        modified = $null
    }

    if (-not (Test-Path $repo.path)) {
        $msg = "$($repo.name): repo directory not found at $($repo.path)"
        Write-Warning "        MISSING -- $msg"
        $errors.Add($msg)
        $result.status = "missing_repo"
    } elseif (-not (Test-Path $dbPath)) {
        $msg = "$($repo.name): .codegraph\db.sqlite missing -- run 'codegraph init -i' inside this repo"
        Write-Warning "        NOT INIT -- $msg"
        $errors.Add($msg)
        $result.status = "not_initialized"
    } else {
        $fi = Get-Item $dbPath
        $sizeKb  = [math]::Round($fi.Length / 1KB, 1)
        $ageH    = [math]::Round(($now - $fi.LastWriteTime).TotalHours, 1)
        $result.size_kb  = $sizeKb
        $result.age_h    = $ageH
        $result.modified = $fi.LastWriteTime.ToUniversalTime().ToString("o")

        if ($sizeKb -lt 10) {
            $msg = "$($repo.name): DB is only $sizeKb KB -- may be empty or corrupt. Re-run: codegraph init -i"
            Write-Warning "        SUSPECT -- $msg"
            $warnings.Add($msg)
            $result.status = "suspect"
        } elseif ($ageH -gt $MaxStaleHours) {
            $msg = "$($repo.name): DB last written $ageH h ago (threshold ${MaxStaleHours}h) -- file watcher may be inactive"
            Write-Warning "        STALE -- $msg"
            $warnings.Add($msg)
            $result.status = "stale"
        } else {
            Write-Host "        OK -- $($repo.name) ($sizeKb KB, ${ageH}h ago)"
            $result.status = "healthy"
        }
    }
    $repoResults.Add([PSCustomObject]$result)
}

# -- Overall status -----------------------------------------------------------
$overall = if ($errors.Count -gt 0) { "error" } elseif ($warnings.Count -gt 0) { "warning" } else { "healthy" }

Write-Status -Data @{
    checked_at      = $checkedAt
    status          = $overall
    binary_version  = $binaryVersion
    mcp_wired       = $mcpWired
    errors          = $errors.ToArray()
    warnings        = $warnings.ToArray()
    repos           = $repoResults.ToArray()
}

# -- Alert if not healthy -----------------------------------------------------
if ($overall -eq "error") {
    $errList = ($errors.ToArray() | ForEach-Object { "`u{2022} $_" }) -join "`n"
    Send-SlackAlert ":rotating_light: *CodeGraph BROKEN* ($($errors.Count) error(s) at $($now.ToString('HH:mm'))):`n$errList`n_See_ ``D:\hermes-backups\codegraph-health.json`` _for full detail._"
    Write-Warning "Probe complete: $($errors.Count) ERROR(s) -- Slack alert sent"
    exit 1
} elseif ($overall -eq "warning") {
    $warnList = ($warnings.ToArray() | ForEach-Object { "`u{2022} $_" }) -join "`n"
    Send-SlackAlert ":warning: *CodeGraph WARNING* ($($warnings.Count) issue(s) at $($now.ToString('HH:mm'))):`n$warnList`n_Indexes may be stale. Open the repo in Claude Code to wake the file watcher._"
    Write-Warning "Probe complete: $($warnings.Count) WARNING(s) -- Slack alert sent"
    exit 0
} else {
    Write-Host "[$($now.ToString('HH:mm:ss'))] Probe complete: all $($Repos.Count) repos healthy. No Slack alert."
    exit 0
}
