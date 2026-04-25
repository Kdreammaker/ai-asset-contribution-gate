param(
    [ValidateSet('local-maintainer', 'external-safe-proxy')]
    [string]$ConnectorMode = 'local-maintainer',
    [string]$PrivateWorkspaceRoot = '',
    [string]$ConnectorProxyUrl = '',
    [string]$AccessKeyId = '',
    [string]$OutputPath = '',
    [switch]$SkipPrivateValidation,
    [switch]$AllowSiblingInference,
    [switch]$ShowPrivatePaths,
    [switch]$CheckUpdates
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

function Protect-PathValue {
    param([string]$Value, [string]$Label)

    if ($ShowPrivatePaths) {
        return $Value
    }
    if ([string]::IsNullOrWhiteSpace($Value)) {
        return ''
    }
    return "[redacted:$Label]"
}

function Protect-PrivateDetails {
    param([object]$Value)

    if ($null -eq $Value) {
        return $null
    }
    if ($Value -is [string]) {
        if (-not [string]::IsNullOrWhiteSpace($privateRoot) -and $Value.StartsWith($privateRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            return '[redacted:private_workspace_path]'
        }
        return $Value
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $copy = [ordered]@{}
        foreach ($key in $Value.Keys) {
            $copy[$key] = Protect-PrivateDetails -Value $Value[$key]
        }
        return $copy
    }
    if ($Value -is [pscustomobject]) {
        $copy = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            $copy[$property.Name] = Protect-PrivateDetails -Value $property.Value
        }
        return $copy
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $items = @()
        foreach ($item in $Value) {
            $items += Protect-PrivateDetails -Value $item
        }
        return $items
    }
    return $Value
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path
$errors = @()
$warnings = @()
$filesRead = @()
$filesWritten = @()
$privateRoot = ''
$assetctlPath = ''
$registryPath = ''
$connectorSchemaPath = ''
$privateExportPath = ''

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot '.assetctl-private-connector.local.json'
}

if ($CheckUpdates) {
    try {
        $updateText = & (Join-Path $PSScriptRoot 'candidate-gate.ps1') -Operation update-check 2>&1
        if ($LASTEXITCODE -eq 0) {
            $update = ($updateText -join [Environment]::NewLine) | ConvertFrom-Json
            if ($update.update_available) {
                $warnings += "A newer public toolkit release is available: $($update.latest_version). Setup will continue."
            }
        }
        else {
            $warnings += "Update check failed with exit code $LASTEXITCODE. Setup will continue."
        }
    }
    catch {
        $warnings += "Update check failed: $($_.Exception.Message). Setup will continue."
    }
}

if ($ConnectorMode -eq 'local-maintainer' -and [string]::IsNullOrWhiteSpace($PrivateWorkspaceRoot) -and $AllowSiblingInference) {
    $candidate = Split-Path -Parent $repoRoot
    $sibling = Join-Path $candidate 'assets achivement for work'
    if (Test-Path -LiteralPath (Join-Path $sibling 'downloaded-assets\tools\assetctl.ps1') -PathType Leaf) {
        $PrivateWorkspaceRoot = $sibling
        $warnings += 'PrivateWorkspaceRoot was inferred only because -AllowSiblingInference was supplied. Pass -PrivateWorkspaceRoot explicitly in automation.'
    }
}

if ($ConnectorMode -eq 'local-maintainer' -and [string]::IsNullOrWhiteSpace($PrivateWorkspaceRoot)) {
    $errors += 'PrivateWorkspaceRoot is required for local-maintainer mode. This command does not guess or clone private repositories by default.'
    $result = New-SetupResult -Ok $false -Errors $errors -Warnings $warnings -NextRecommendedAction 'Run with -PrivateWorkspaceRoot "<owner-approved-private-workspace>" or use -ConnectorMode external-safe-proxy with owner-provided proxy metadata.'
    $result | ConvertTo-Json -Depth 12
    exit 1
}

if ($ConnectorMode -eq 'external-safe-proxy' -and [string]::IsNullOrWhiteSpace($ConnectorProxyUrl) -and [string]::IsNullOrWhiteSpace($AccessKeyId)) {
    $errors += 'external-safe-proxy mode requires -ConnectorProxyUrl or -AccessKeyId metadata from the owner. Do not store access-key secrets in this public toolkit.'
    $result = New-SetupResult -Ok $false -Errors $errors -Warnings $warnings -NextRecommendedAction 'Ask the owner for scoped connector proxy metadata or an access-key identifier, not a secret.'
    $result | ConvertTo-Json -Depth 12
    exit 1
}

if ($ConnectorMode -eq 'local-maintainer') {
    try {
        $privateRoot = Resolve-RequiredPath $PrivateWorkspaceRoot
    }
    catch {
        $errors += "PrivateWorkspaceRoot could not be resolved: $($_.Exception.Message)"
        $result = New-SetupResult -Ok $false -Errors $errors -Warnings $warnings -NextRecommendedAction 'Check the owner-approved private workspace path and rerun setup.'
        $result | ConvertTo-Json -Depth 12
        exit 1
    }

    $assetctlPath = Join-Path $privateRoot 'downloaded-assets\tools\assetctl.ps1'
    $registryPath = Join-Path $privateRoot 'downloaded-assets\registry\asset-registry.jsonl'
    $connectorSchemaPath = Join-Path $privateRoot 'downloaded-assets\connector\schemas'
    $privateExportPath = Join-Path $privateRoot 'downloaded-assets\_work\public-cli-asset-export\exports\latest\metadata\public-cli-assets.jsonl'

    $requiredPaths = @(
        @{ Path = $assetctlPath; Label = 'private_assetctl' },
        @{ Path = $registryPath; Label = 'private_registry' },
        @{ Path = $connectorSchemaPath; Label = 'private_connector_schemas' }
    )
    foreach ($required in $requiredPaths) {
        if (-not (Test-Path -LiteralPath $required.Path)) {
            $errors += "Required private connector path is missing: $($required.Label)"
        }
        else {
            $filesRead += (Protect-PathValue -Value $required.Path -Label $required.Label)
        }
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
if ($ConnectorMode -eq 'local-maintainer' -and -not $SkipPrivateValidation -and $errors.Count -eq 0) {
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
        connector_mode = $ConnectorMode
        public_toolkit_root = $repoRoot
        private_workspace_root = if ($ConnectorMode -eq 'local-maintainer') { $privateRoot } else { '' }
        private_assetctl = if ($ConnectorMode -eq 'local-maintainer') { $assetctlPath } else { '' }
        public_safe_metadata_export = if ($ConnectorMode -eq 'local-maintainer') { $privateExportPath } else { '' }
        connector_proxy_url = $ConnectorProxyUrl
        access_key_id = $AccessKeyId
        access_key_secret_storage = 'not_stored_by_public_toolkit'
        generated_at_utc = [DateTime]::UtcNow.ToString('o')
        safety = [ordered]@{
            keep_private_registry_out_of_public_repo = $true
            keep_raw_assets_out_of_public_repo = $true
            connector_requests_redact_private_storage_refs_by_default = $true
            binary_materialization_requires_private_workspace_approval = $true
            private_workspace_path_was_explicit_or_opt_in = ($ConnectorMode -ne 'local-maintainer' -or -not [string]::IsNullOrWhiteSpace($PrivateWorkspaceRoot) -or $AllowSiblingInference)
            private_repo_auto_clone = $false
            private_path_guessing_by_default = $false
            access_key_secret_persisted = $false
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
    connector_mode = $ConnectorMode
    public_toolkit_root = $repoRoot
    private_workspace_root = Protect-PathValue -Value $privateRoot -Label 'private_workspace_root'
    private_assetctl = Protect-PathValue -Value $assetctlPath -Label 'private_assetctl'
    connector_proxy_url = if ([string]::IsNullOrWhiteSpace($ConnectorProxyUrl)) { '' } else { '[configured]' }
    access_key_id = if ([string]::IsNullOrWhiteSpace($AccessKeyId)) { '' } else { '[configured]' }
    local_connector_config = $OutputPath
    public_validation = $publicValidation
    private_capabilities = Protect-PrivateDetails -Value $privateCapabilities
    private_export_present = if ($ConnectorMode -eq 'local-maintainer' -and -not [string]::IsNullOrWhiteSpace($privateExportPath)) { (Test-Path -LiteralPath $privateExportPath -PathType Leaf) } else { $false }
}

$next = if ($ok) {
    if ($ConnectorMode -eq 'local-maintainer') {
        'Run connector-client new-request in the public toolkit, then run private assetctl connector-search or connector-materialize-plan in the private workspace.'
    }
    else {
        'Use connector-client new-request to create public-safe requests, then submit through the owner-provided proxy or scoped connector flow.'
    }
}
else {
    'Fix the missing private workspace path or connector readiness issue, then rerun setup.'
}

$result = New-SetupResult -Ok $ok -Errors $errors -Warnings $warnings -Outputs $outputs -FilesRead $filesRead -FilesWritten $filesWritten -NextRecommendedAction $next
$result | ConvertTo-Json -Depth 16
if (-not $ok) {
    exit 1
}
