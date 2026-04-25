param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [switch]$CheckUpdates,
    [switch]$SkipValidation,
    [switch]$PrivateValidation,
    [switch]$ShowPrivatePaths,
    [string]$ProfileName = 'default'
)

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

function New-Check {
    param(
        [string]$Name,
        [bool]$Ok,
        [string]$Message,
        [object]$Details = $null,
        [bool]$WarningOnly = $false
    )

    return [ordered]@{
        name = $Name
        ok = $Ok
        warning_only = $WarningOnly
        message = $Message
        details = $Details
    }
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
    param([object]$Value, [string]$PrivateRoot)

    if ($null -eq $Value) {
        return $null
    }
    if ($Value -is [string]) {
        if (-not [string]::IsNullOrWhiteSpace($PrivateRoot) -and $Value.StartsWith($PrivateRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
            return '[redacted:private_workspace_path]'
        }
        return $Value
    }
    if ($Value -is [System.Collections.IDictionary]) {
        $copy = [ordered]@{}
        foreach ($key in $Value.Keys) {
            $copy[$key] = Protect-PrivateDetails -Value $Value[$key] -PrivateRoot $PrivateRoot
        }
        return $copy
    }
    if ($Value -is [pscustomobject]) {
        $copy = [ordered]@{}
        foreach ($property in $Value.PSObject.Properties) {
            $copy[$property.Name] = Protect-PrivateDetails -Value $property.Value -PrivateRoot $PrivateRoot
        }
        return $copy
    }
    if ($Value -is [System.Collections.IEnumerable]) {
        $items = @()
        foreach ($item in $Value) {
            $items += Protect-PrivateDetails -Value $item -PrivateRoot $PrivateRoot
        }
        return $items
    }
    return $Value
}

function Invoke-JsonCommand {
    param(
        [string]$Name,
        [string]$FilePath,
        [hashtable]$Parameters,
        [bool]$WarningOnly = $false
    )

    try {
        if ($null -eq $Parameters) {
            $Parameters = @{}
        }
        $text = & $FilePath @Parameters 2>&1
        $commandSucceeded = $?
        $exitCode = 0
        if ($null -ne $LASTEXITCODE -and -not [string]::IsNullOrWhiteSpace([string]$LASTEXITCODE)) {
            $exitCode = [int]$LASTEXITCODE
        }
        elseif (-not $commandSucceeded) {
            $exitCode = 1
        }
        $joined = ($text -join [Environment]::NewLine).Trim()
        $parsed = $null
        if (-not [string]::IsNullOrWhiteSpace($joined)) {
            $parsed = $joined | ConvertFrom-Json
        }
        if ($exitCode -ne 0) {
            return New-Check -Name $Name -Ok $false -WarningOnly $WarningOnly -Message "Command exited $exitCode." -Details @{ output = $joined }
        }
        $innerOk = $true
        if ($parsed -and ($parsed.PSObject.Properties.Name -contains 'ok')) {
            $innerOk = [bool]$parsed.ok
        }
        return New-Check -Name $Name -Ok $innerOk -WarningOnly $WarningOnly -Message 'Command completed.' -Details $parsed
    }
    catch {
        return New-Check -Name $Name -Ok $false -WarningOnly $WarningOnly -Message $_.Exception.Message
    }
}

$repoRoot = (Resolve-Path -LiteralPath $Root).Path
$checks = @()
$warnings = @()
$errors = @()
$connectorState = [ordered]@{
    configured = $false
    config_path = '.assetctl-private-connector.local.json'
    mode = 'not_configured'
    private_workspace_root = ''
    private_assetctl = ''
    proxy_url = ''
    access_key_id = ''
}
$userProfileState = [ordered]@{
    profile_name = $ProfileName
    configured = $false
    connector_mode = 'not_configured'
    user_authorized = $false
}

$extensionPath = Join-Path $repoRoot 'assetctl-extension.json'
if (Test-Path -LiteralPath $extensionPath -PathType Leaf) {
    try {
        $extension = Get-Content -Encoding UTF8 -LiteralPath $extensionPath -Raw | ConvertFrom-Json
        $checks += New-Check -Name 'extension-manifest' -Ok $true -Message 'assetctl-extension.json parsed.' -Details @{ version = $extension.version; default_mode = $extension.default_mode }
    }
    catch {
        $checks += New-Check -Name 'extension-manifest' -Ok $false -Message "assetctl-extension.json failed to parse: $($_.Exception.Message)"
    }
}
else {
    $checks += New-Check -Name 'extension-manifest' -Ok $false -Message 'assetctl-extension.json is missing.'
}

$requiredDirs = @('reports', 'reports\connector', '.assetctl', '.assetctl\requests', '.assetctl\cache')
foreach ($dir in $requiredDirs) {
    $path = Join-Path $repoRoot $dir
    $checks += New-Check -Name "local-dir:$dir" -Ok (Test-Path -LiteralPath $path -PathType Container) -Message "$dir should exist after bootstrap."
}

$python = Get-Command python -ErrorAction SilentlyContinue
$git = Get-Command git -ErrorAction SilentlyContinue
$node = Get-Command node -ErrorAction SilentlyContinue
$checks += New-Check -Name 'runtime:powershell' -Ok ($PSVersionTable.PSVersion.Major -ge 5) -Message "PowerShell $($PSVersionTable.PSVersion) detected." -Details @{ version = "$($PSVersionTable.PSVersion)" }
$checks += New-Check -Name 'runtime:python' -Ok ([bool]$python) -Message $(if ($python) { 'python is available.' } else { 'python is required but was not found.' })
$checks += New-Check -Name 'runtime:git' -Ok $true -WarningOnly $true -Message $(if ($git) { 'git is available.' } else { 'git is recommended but was not found.' })
$checks += New-Check -Name 'runtime:node' -Ok $true -WarningOnly $true -Message $(if ($node) { 'node is optional and was found.' } else { 'node is optional and was not found.' })

if (-not $SkipValidation) {
    $checks += Invoke-JsonCommand -Name 'candidate-fixtures' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'validate-fixtures'; AssetsRoot = $repoRoot }
    $checks += Invoke-JsonCommand -Name 'connector-fixtures' -FilePath (Join-Path $repoRoot 'tools\connector-client.ps1') -Parameters @{ Operation = 'validate-fixtures'; Root = $repoRoot }
    $checks += Invoke-JsonCommand -Name 'public-leak-scan' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'leak-scan'; Path = $repoRoot }
    $checks += Invoke-JsonCommand -Name 'version' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'version' }
}
else {
    $warnings += 'Validation was skipped by -SkipValidation.'
}

if ($CheckUpdates) {
    $checks += Invoke-JsonCommand -Name 'update-check' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'update-check' } -WarningOnly $true
}

$profileCheck = Invoke-JsonCommand -Name 'user-profile-status' -FilePath (Join-Path $repoRoot 'tools\user-profile.ps1') -Parameters @{ Operation = 'status'; Root = $repoRoot; ProfileName = $ProfileName } -WarningOnly $true
if ($profileCheck.details -and $profileCheck.details.outputs) {
    $profileOutputs = $profileCheck.details.outputs
    $userProfileState.profile_name = $profileOutputs.profile_name
    $userProfileState.configured = [bool]$profileOutputs.profile_configured
    if ($profileOutputs.connector_mode) { $userProfileState.connector_mode = $profileOutputs.connector_mode }
    if ($profileOutputs.user_authorized) { $userProfileState.user_authorized = [bool]$profileOutputs.user_authorized }
}
$checks += $profileCheck

$configPath = Join-Path $repoRoot '.assetctl-private-connector.local.json'
if (Test-Path -LiteralPath $configPath -PathType Leaf) {
    try {
        $config = Get-Content -Encoding UTF8 -LiteralPath $configPath -Raw | ConvertFrom-Json
        $connectorState.configured = $true
        $connectorState.mode = if ($config.connector_mode) { $config.connector_mode } else { 'local-maintainer' }
        $connectorState.private_workspace_root = Protect-PathValue -Value $config.private_workspace_root -Label 'private_workspace_root'
        $connectorState.private_assetctl = Protect-PathValue -Value $config.private_assetctl -Label 'private_assetctl'
        $connectorState.proxy_url = if ($config.connector_proxy_url) { '[configured]' } else { '' }
        $connectorState.access_key_id = if ($config.access_key_id) { '[configured]' } else { '' }
        $checks += New-Check -Name 'private-connector-config' -Ok $true -Message 'Ignored local private connector config is present.' -Details $connectorState
        if ($PrivateValidation -and $config.private_assetctl) {
            $privateCheck = Invoke-JsonCommand -Name 'private-connector-capabilities' -FilePath $config.private_assetctl -Parameters @{ Command = 'connector-capabilities' }
            $privateCheck.details = Protect-PrivateDetails -Value $privateCheck.details -PrivateRoot $config.private_workspace_root
            $checks += $privateCheck
        }
        elseif ($PrivateValidation) {
            $checks += New-Check -Name 'private-connector-capabilities' -Ok $false -Message 'Private validation requested, but no local private assetctl path is configured.'
        }
    }
    catch {
        $checks += New-Check -Name 'private-connector-config' -Ok $false -Message "Private connector config failed to parse: $($_.Exception.Message)"
    }
}
else {
    $checks += New-Check -Name 'private-connector-config' -Ok $true -WarningOnly $true -Message 'No private connector config found; public toolkit remains fixture-only.'
}

foreach ($check in $checks) {
    if (-not $check.ok) {
        if ($check.warning_only) {
            $warnings += "$($check.name): $($check.message)"
        }
        else {
            $errors += "$($check.name): $($check.message)"
        }
    }
}

$ok = ($errors.Count -eq 0)
$result = [ordered]@{
    ok = $ok
    operation_type = 'assetctl_public_doctor'
    schema_version = '1.0'
    root = $repoRoot
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    checks = $checks
    warnings = $warnings
    errors = $errors
    user_profile_state = $userProfileState
    connector_state = $connectorState
    next_recommended_action = if ($ok -and $userProfileState.configured -and -not $connectorState.configured) { 'Run .\tools\user-profile.ps1 -Operation attach, or rerun bootstrap to auto-attach the authorized profile.' } elseif ($ok -and -not $connectorState.configured) { 'Public toolkit is ready in fixture-only mode. Run user-profile authorize only after the user allows connector access.' } elseif ($ok) { 'Toolkit is ready. Use connector-client for public-safe requests.' } else { 'Run bootstrap or fix failed checks, then rerun doctor.' }
}

$result | ConvertTo-Json -Depth 18
if (-not $ok) {
    exit 1
}
