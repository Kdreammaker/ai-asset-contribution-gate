param(
    [ValidateSet('validate-fixtures', 'new-request', 'validate-request', 'validate-response', 'search-metadata')]
    [string]$Operation = 'validate-fixtures',
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$InputPath = '',
    [string]$OutputPath = '',
    [string]$RequestType = 'asset_search',
    [string]$RequestId = '',
    [string]$Query = '',
    [string]$Intent = '',
    [string]$Locale = 'auto',
    [string]$AssetTypes = '',
    [string]$AssetType = '',
    [string]$DeliveryMode = 'metadata_only',
    [int]$Limit = 10,
    [switch]$CheckUpdates
)

$ErrorActionPreference = 'Stop'

if ($CheckUpdates) {
    try {
        $updateText = & (Join-Path $PSScriptRoot 'candidate-gate.ps1') -Operation update-check 2>&1
        if ($LASTEXITCODE -eq 0) {
            $update = ($updateText -join [Environment]::NewLine) | ConvertFrom-Json
            if ($update.update_available) {
                Write-Warning "A newer public toolkit release is available: $($update.latest_version). Current connector command will continue."
            }
        }
        else {
            Write-Warning "Update check failed with exit code $LASTEXITCODE. Current connector command will continue."
        }
    }
    catch {
        Write-Warning "Update check failed: $($_.Exception.Message). Current connector command will continue."
    }
}

$python = (Get-Command python -ErrorAction Stop).Source
$script = Join-Path $PSScriptRoot 'connector_client.py'
$argsList = @($script, $Operation)

switch ($Operation) {
    'validate-fixtures' {
        $argsList += @('--root', $Root)
    }
    'new-request' {
        if ([string]::IsNullOrWhiteSpace($Query)) { throw 'new-request requires -Query.' }
        $argsList += @('--request-type', $RequestType, '--query', $Query, '--locale', $Locale, '--asset-types', $AssetTypes, '--delivery-mode', $DeliveryMode, '--limit', ([string]$Limit))
        if (-not [string]::IsNullOrWhiteSpace($RequestId)) { $argsList += @('--request-id', $RequestId) }
        if (-not [string]::IsNullOrWhiteSpace($Intent)) { $argsList += @('--intent', $Intent) }
        if (-not [string]::IsNullOrWhiteSpace($OutputPath)) { $argsList += @('--output-path', $OutputPath) }
    }
    'validate-request' {
        if ([string]::IsNullOrWhiteSpace($InputPath)) { throw 'validate-request requires -InputPath.' }
        $argsList += @('--input-path', $InputPath)
    }
    'validate-response' {
        if ([string]::IsNullOrWhiteSpace($InputPath)) { throw 'validate-response requires -InputPath.' }
        $argsList += @('--input-path', $InputPath)
    }
    'search-metadata' {
        if ([string]::IsNullOrWhiteSpace($InputPath)) { throw 'search-metadata requires -InputPath.' }
        if ([string]::IsNullOrWhiteSpace($Query)) { throw 'search-metadata requires -Query.' }
        $argsList += @('--input-path', $InputPath, '--query', $Query, '--limit', ([string]$Limit))
        if (-not [string]::IsNullOrWhiteSpace($AssetType)) { $argsList += @('--asset-type', $AssetType) }
    }
}

& $python @argsList
$pythonExitCode = $LASTEXITCODE
if ($pythonExitCode -ne 0) {
    exit $pythonExitCode
}
