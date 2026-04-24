param(
    [string]$PrivateWorkspaceRoot = '',
    [string]$OutputPath = '',
    [switch]$SkipPrivateValidation
)

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

function New-SetupResult {
    param(
        [bool]$Ok,
        [object[]]$Errors = @(),
        [object[]]$Warnings = @(),
        [hashtable]$Outputs = @{},
        [string[]]$FilesRead = @(),
        [string[]]$FilesWritten = @(),
        [string]$NextRecommendedAction = ''
    )

    return [ordered]@{
        ok = $Ok
        operation_type = 'private_connector_setup'
        schema_version = '1.0'
        outputs = $Outputs
        warnings = @($Warnings)
        errors = @($Errors)
        files_read = @($FilesRead)
        files_written = @($FilesWritten)
        next_recommended_action = $NextRecommendedAction
    }
}

function Resolve-RequiredPath {
    param([string]$PathText)

    if ([string]::IsNullOrWhiteSpace($PathText)) {
        throw 'Path is required.'
    }
    return (Resolve-Path -LiteralPath $PathText -ErrorAction Stop).Path
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$errors = @()
$warnings = @()
$filesRead = @()
$filesWritten = @()

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot '.assetctl-private-connector.local.json'
}

if ([string]::IsNullOrWhiteSpace($PrivateWorkspaceRoot)) {
    $candidate = Split-Path -Parent $repoRoot
    $sibling = Join-Path $candidate 'assets achivement for work'
    if (Test-Path -LiteralPath (Join-Path $sibling 'downloaded-assets\tools\assetctl.ps1') -PathType Leaf) {
        $PrivateWorkspaceRoot = $sibling
        $warnings += 'PrivateWorkspaceRoot was inferred from a sibling workspace. Pass -PrivateWorkspaceRoot explicitly in automation.'
    }
}

if ([string]::IsNullOrWhiteSpace($PrivateWorkspaceRoot)) {
    $errors += 'PrivateWorkspaceRoot is required. Pass the local private workspace root that contains downloaded-assets/tools/assetctl.ps1.'
    $result = New-SetupResult -Ok $false -Errors $errors -Warnings $warnings -NextRecommendedAction 'Run with -PrivateWorkspaceRoot "<path-to-private-workspace>".'
    $result | ConvertTo-Json -Depth 12
    exit 1
}

try {
    $privateRoot = Resolve-RequiredPath $PrivateWorkspaceRoot
}
catch {
    $errors += "PrivateWorkspaceRoot could not be resolved: $($_.Exception.Message)"
    $result = New-SetupResult -Ok $false -Errors $errors -Warnings $warnings -NextRecommendedAction 'Check the private workspace path and rerun setup.'
    $result | ConvertTo-Json -Depth 12
    exit 1
}

$assetctlPath = Join-Path $privateRoot 'downloaded-assets\tools\assetctl.ps1'
$registryPath = Join-Path $privateRoot 'downloaded-assets\registry\asset-registry.jsonl'
$connectorSchemaPath = Join-Path $privateRoot 'downloaded-assets\connector\schemas'
$privateExportPath = Join-Path $privateRoot 'downloaded-assets\_work\public-cli-asset-export\exports\latest\metadata\public-cli-assets.jsonl'

foreach ($required in @($assetctlPath, $registryPath, $connectorSchemaPath)) {
    if (-not (Test-Path -LiteralPath $required)) {
        $errors += "Required private connector path is missing: $required"
    }
    else {
        $filesRead += $required
    }
}

$publicValidation = $null
try {
    $publicValidationText = & (Join-Path $PSScriptRoot 'connector-client.ps1') -Operation validate-fixtures 2>&1
    if ($LASTEXITCODE -ne 0) {
        $errors += "Public connector fixture validation failed with exit code $LASTEXITCODE."
    }
    else {
        $publicValidation = ($publicValidationText -join [Environment]::NewLine) | ConvertFrom-Json
    }
}
catch {
    $errors += "Public connector fixture validation failed: $($_.Exception.Message)"
}

$privateCapabilities = $null
if (-not $SkipPrivateValidation -and $errors.Count -eq 0) {
    try {
        $privateValidationText = & $assetctlPath connector-capabilities 2>&1
        if ($LASTEXITCODE -ne 0) {
            $errors += "Private connector capability check failed with exit code $LASTEXITCODE."
        }
        else {
            $privateCapabilities = ($privateValidationText -join [Environment]::NewLine) | ConvertFrom-Json
        }
    }
    catch {
        $errors += "Private connector capability check failed: $($_.Exception.Message)"
    }
}

if ($errors.Count -eq 0) {
    $config = [ordered]@{
        schema_version = '1.0'
        config_type = 'assetctl_private_connector_local'
        public_toolkit_root = $repoRoot
        private_workspace_root = $privateRoot
        private_assetctl = $assetctlPath
        public_safe_metadata_export = $privateExportPath
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        safety = [ordered]@{
            keep_private_registry_out_of_public_repo = $true
            keep_raw_assets_out_of_public_repo = $true
            connector_requests_redact_private_storage_refs_by_default = $true
            binary_materialization_requires_private_workspace_approval = $true
        }
        smoke_commands = @(
            '.\tools\connector-client.ps1 -Operation validate-fixtures',
            '& "<private_assetctl>" connector-capabilities',
            '& "<private_assetctl>" connector-search -Query "dashboard security icon" -Limit 3',
            '& "<private_assetctl>" connector-materialize-plan -InputPath ".\downloaded-assets\connector\fixtures\asset-request.example.json"'
        )
    }

    $json = $config | ConvertTo-Json -Depth 12
    $encoding = New-Object System.Text.UTF8Encoding($false)
    $outputParent = Split-Path -Parent $OutputPath
    if (-not [string]::IsNullOrWhiteSpace($outputParent)) {
        New-Item -ItemType Directory -Force -Path $outputParent | Out-Null
    }
    [System.IO.File]::WriteAllText($OutputPath, $json + [Environment]::NewLine, $encoding)
    $filesWritten += $OutputPath
}

$ok = ($errors.Count -eq 0)
$outputs = @{
    public_toolkit_root = $repoRoot
    private_workspace_root = if ($privateRoot) { $privateRoot } else { '' }
    local_connector_config = $OutputPath
    public_validation = $publicValidation
    private_capabilities = $privateCapabilities
    private_export_present = (Test-Path -LiteralPath $privateExportPath -PathType Leaf)
}

$next = if ($ok) {
    'Run connector-client new-request in the public toolkit, then run private assetctl connector-search or connector-materialize-plan in the private workspace.'
}
else {
    'Fix the missing private workspace path or connector readiness issue, then rerun setup.'
}

$result = New-SetupResult -Ok $ok -Errors $errors -Warnings $warnings -Outputs $outputs -FilesRead $filesRead -FilesWritten $filesWritten -NextRecommendedAction $next
$result | ConvertTo-Json -Depth 16
if (-not $ok) {
    exit 1
}
