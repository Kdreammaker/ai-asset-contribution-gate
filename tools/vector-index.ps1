param(
    [ValidateSet('build', 'query', 'validate-fixtures')]
    [string]$Operation = 'query',
    [string]$InputPath = '',
    [string]$IndexPath = '',
    [string]$OutputPath = '',
    [string]$Query = '',
    [string]$AssetType = '',
    [int]$Limit = 10,
    [string]$FixturePath = ''
)

$ErrorActionPreference = 'Stop'

$python = (Get-Command python -ErrorAction Stop).Source
$script = Join-Path $PSScriptRoot 'vector_index.py'
$argsList = @($script, $Operation)

switch ($Operation) {
    'build' {
        if ([string]::IsNullOrWhiteSpace($InputPath)) { throw 'build requires -InputPath.' }
        if ([string]::IsNullOrWhiteSpace($OutputPath)) { throw 'build requires -OutputPath.' }
        $argsList += @('--input-path', $InputPath, '--output-path', $OutputPath)
    }
    'query' {
        if ([string]::IsNullOrWhiteSpace($IndexPath)) { throw 'query requires -IndexPath.' }
        if ([string]::IsNullOrWhiteSpace($Query)) { throw 'query requires -Query.' }
        $argsList += @('--index-path', $IndexPath, '--query', $Query, '--limit', ([string]$Limit))
        if (-not [string]::IsNullOrWhiteSpace($AssetType)) { $argsList += @('--asset-type', $AssetType) }
    }
    'validate-fixtures' {
        if (-not [string]::IsNullOrWhiteSpace($FixturePath)) { $argsList += @('--fixture-path', $FixturePath) }
        if (-not [string]::IsNullOrWhiteSpace($OutputPath)) { $argsList += @('--output-path', $OutputPath) }
    }
}

& $python @argsList
$pythonExitCode = $LASTEXITCODE
if ($pythonExitCode -ne 0) {
    exit $pythonExitCode
}
