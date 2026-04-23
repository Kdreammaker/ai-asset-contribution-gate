param(
    [ValidateSet('add', 'review', 'promote', 'validate-fixtures', 'leak-scan', 'version', 'update-check')]
    [string]$Operation = 'review',
    [string]$AssetsRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$File = '',
    [string]$Metadata = '',
    [string]$InputPath = '',
    [string]$Path = '',
    [string]$OutputPath = '',
    [string]$FixtureRoot = '',
    [string]$CandidateId = '',
    [string]$CandidateType = 'asset_candidate',
    [string]$SubmittedByRole = 'user',
    [string]$SourceUrl = '',
    [string]$SourceName = '',
    [string]$DeclaredLicense = '',
    [string]$DeclaredCommercialUseAllowed = '',
    [string]$DeclaredAttributionRequired = '',
    [string]$AssetType = 'unknown',
    [string]$IntendedUse = '',
    [string]$Notes = '',
    [string]$ActorRole = 'user',
    [string]$CurrentVersion = '',
    [string]$Repository = '',
    [int]$TimeoutSeconds = 10,
    [switch]$Apply,
    [switch]$Approve
)

$ErrorActionPreference = 'Stop'

$python = (Get-Command python -ErrorAction Stop).Source
$script = Join-Path $PSScriptRoot 'candidate_gate.py'
$argsList = @($script, $Operation)

if ($Operation -notin @('leak-scan', 'version', 'update-check')) {
    $argsList += @('--assets-root', $AssetsRoot)
}
if (-not [string]::IsNullOrWhiteSpace($OutputPath)) { $argsList += @('--output-path', $OutputPath) }

switch ($Operation) {
    'add' {
        if (-not [string]::IsNullOrWhiteSpace($File)) { $argsList += @('--file', $File) }
        if (-not [string]::IsNullOrWhiteSpace($Metadata)) { $argsList += @('--metadata', $Metadata) }
        if (-not [string]::IsNullOrWhiteSpace($CandidateId)) { $argsList += @('--candidate-id', $CandidateId) }
        if (-not [string]::IsNullOrWhiteSpace($CandidateType)) { $argsList += @('--candidate-type', $CandidateType) }
        if (-not [string]::IsNullOrWhiteSpace($SubmittedByRole)) { $argsList += @('--submitted-by-role', $SubmittedByRole) }
        if (-not [string]::IsNullOrWhiteSpace($SourceUrl)) { $argsList += @('--source-url', $SourceUrl) }
        if (-not [string]::IsNullOrWhiteSpace($SourceName)) { $argsList += @('--source-name', $SourceName) }
        if (-not [string]::IsNullOrWhiteSpace($DeclaredLicense)) { $argsList += @('--declared-license', $DeclaredLicense) }
        if (-not [string]::IsNullOrWhiteSpace($DeclaredCommercialUseAllowed)) { $argsList += @('--declared-commercial-use-allowed', $DeclaredCommercialUseAllowed) }
        if (-not [string]::IsNullOrWhiteSpace($DeclaredAttributionRequired)) { $argsList += @('--declared-attribution-required', $DeclaredAttributionRequired) }
        if (-not [string]::IsNullOrWhiteSpace($AssetType)) { $argsList += @('--asset-type', $AssetType) }
        if (-not [string]::IsNullOrWhiteSpace($IntendedUse)) { $argsList += @('--intended-use', $IntendedUse) }
        if (-not [string]::IsNullOrWhiteSpace($Notes)) { $argsList += @('--notes', $Notes) }
    }
    'review' {
        if (-not [string]::IsNullOrWhiteSpace($InputPath)) { $argsList += @('--input-path', $InputPath) }
        if ($Apply) { $argsList += '--apply' }
    }
    'promote' {
        if (-not [string]::IsNullOrWhiteSpace($InputPath)) { $argsList += @('--input-path', $InputPath) }
        if (-not [string]::IsNullOrWhiteSpace($ActorRole)) { $argsList += @('--actor-role', $ActorRole) }
        if ($Approve) { $argsList += '--approve' }
    }
    'validate-fixtures' {
        if (-not [string]::IsNullOrWhiteSpace($FixtureRoot)) { $argsList += @('--fixture-root', $FixtureRoot) }
    }
    'leak-scan' {
        if ([string]::IsNullOrWhiteSpace($Path)) {
            throw 'leak-scan requires -Path.'
        }
        $argsList += @('--path', $Path)
    }
    'version' {
    }
    'update-check' {
        if (-not [string]::IsNullOrWhiteSpace($CurrentVersion)) { $argsList += @('--current-version', $CurrentVersion) }
        if (-not [string]::IsNullOrWhiteSpace($Repository)) { $argsList += @('--repository', $Repository) }
        $argsList += @('--timeout-seconds', ([string]$TimeoutSeconds))
    }
}

& $python @argsList
$pythonExitCode = $LASTEXITCODE
if ($pythonExitCode -ne 0) {
    exit $pythonExitCode
}
