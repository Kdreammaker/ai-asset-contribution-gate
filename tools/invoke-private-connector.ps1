param(
    [ValidateSet('capabilities', 'search', 'build-ppt-dry-run')]
    [string]$Operation = 'search',
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$ConfigPath = '',
    [string]$InputPath = '',
    [string]$Query = '',
    [string]$AssetType = '',
    [int]$Limit = 10
)

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

function New-Result {
    param(
        [bool]$Ok,
        [object]$Outputs = @{},
        [object[]]$Errors = @(),
        [object[]]$Warnings = @(),
        [string[]]$FilesRead = @(),
        [string]$NextRecommendedAction = ''
    )
    return [ordered]@{
        ok = $Ok
        operation_type = "public_local_private_connector_$Operation"
        schema_version = '1.0'
        outputs = $Outputs
        warnings = @($Warnings)
        errors = @($Errors)
        files_read = @($FilesRead)
        files_written = @()
        next_recommended_action = $NextRecommendedAction
    }
}

function Protect-PathValue {
    param([string]$Value, [string]$Label)
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    return "[redacted:$Label]"
}

$repoRoot = (Resolve-Path -LiteralPath $Root).Path
if ([string]::IsNullOrWhiteSpace($ConfigPath)) {
    $ConfigPath = Join-Path $repoRoot '.assetctl-private-connector.local.json'
}

$errors = @()
$warnings = @()
$filesRead = @()

if (-not (Test-Path -LiteralPath $ConfigPath -PathType Leaf)) {
    $errors += 'No local private connector config found. Run user-profile authorize/attach first.'
    New-Result -Ok $false -Errors $errors -NextRecommendedAction 'Use public-only bundle-request for other PCs, or attach a local-maintainer profile on this machine.' | ConvertTo-Json -Depth 12
    exit 1
}

$config = Get-Content -Raw -Encoding UTF8 -LiteralPath $ConfigPath | ConvertFrom-Json
$filesRead += '.assetctl-private-connector.local.json'

if ($config.connector_mode -ne 'local-maintainer') {
    $errors += 'invoke-private-connector supports only explicitly attached local-maintainer profiles. For other PCs, use bundle-request handoff.'
}
if ([string]::IsNullOrWhiteSpace($config.private_assetctl) -or -not (Test-Path -LiteralPath $config.private_assetctl -PathType Leaf)) {
    $errors += 'Configured private assetctl path is missing or unavailable.'
}
if ($errors.Count -gt 0) {
    New-Result -Ok $false -Errors $errors -FilesRead $filesRead -NextRecommendedAction 'Use bundle-request for public-only workflows, or reattach a valid local-maintainer profile.' | ConvertTo-Json -Depth 12
    exit 1
}

$command = switch ($Operation) {
    'capabilities' { 'connector-capabilities' }
    'search' { 'connector-search' }
    'build-ppt-dry-run' { 'connector-build-ppt-dry-run' }
}

$privateParams = @{ Limit = $Limit }
if (-not [string]::IsNullOrWhiteSpace($InputPath)) { $privateParams.InputPath = $InputPath }
if (-not [string]::IsNullOrWhiteSpace($Query)) { $privateParams.Query = $Query }
if (-not [string]::IsNullOrWhiteSpace($AssetType)) { $privateParams.AssetType = $AssetType }

$raw = & $config.private_assetctl $command @privateParams 2>&1
$exitCode = $LASTEXITCODE
$joined = ($raw -join [Environment]::NewLine).Trim()
$parsed = $null
if (-not [string]::IsNullOrWhiteSpace($joined)) {
    try { $parsed = $joined | ConvertFrom-Json }
    catch { $warnings += 'Private connector output was not JSON parseable.' }
}
if ($exitCode -ne 0) {
    $errors += "Private connector command exited $exitCode."
}
if ($parsed -and ($parsed.PSObject.Properties.Name -contains 'ok') -and -not [bool]$parsed.ok) {
    $errors += 'Private connector returned ok=false.'
}

$outputs = [ordered]@{
    connector_mode = 'local-maintainer'
    private_assetctl = Protect-PathValue -Value $config.private_assetctl -Label 'private_assetctl'
    command = $command
    response = $parsed
}

$ok = ($errors.Count -eq 0)
New-Result -Ok $ok -Outputs $outputs -Errors $errors -Warnings $warnings -FilesRead $filesRead -NextRecommendedAction $(if ($ok) { 'Use returned connector metadata; do not copy private paths or raw private assets into this public repo.' } else { 'Review connector config and private command output.' }) | ConvertTo-Json -Depth 16
if (-not $ok) { exit 1 }
