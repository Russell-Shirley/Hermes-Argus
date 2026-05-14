param([Parameter(Mandatory)][ValidateSet('deepseek','gemma')][string]$Mode)
$ErrorActionPreference = 'Stop'
$repo = "C:\Users\Russell\Documents\GitHub\Hermes-Argus"
$src = "$repo\cognee-server\.env.llm.$Mode"
$dst = "$repo\cognee-server\.env.llm.active"
if (-not (Test-Path $src)) { throw "Missing profile: $src" }
Copy-Item $src $dst -Force
Write-Host "Switched LLM profile to: $Mode"
Write-Host "Restart cognee-server to apply: docker compose -p hermes-argus restart cognee-server"
