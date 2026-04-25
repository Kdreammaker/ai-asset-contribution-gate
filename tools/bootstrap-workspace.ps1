param(
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$OutputPath = '',
    [switch]$SkipUpdateCheck,
    [switch]$SkipValidation,
    [switch]$SkipUserProfileAutoAttach,
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
        [object]$Details = $null
    )

    return [ordered]@{
        name = $Name
        ok = $Ok
        message = $Message
        details = $Details
    }
}

function Invoke-JsonCommand {
    param(
        [string]$Name,
        [string]$FilePath,
        [hashtable]$Parameters,
        [bool]$SoftFail = $false
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
            return New-Check -Name $Name -Ok $false -Message "Command exited $exitCode." -Details @{ output = $joined; soft_fail = $SoftFail }
        }
        $innerOk = $true
        if ($parsed -and ($parsed.PSObject.Properties.Name -contains 'ok')) {
            $innerOk = [bool]$parsed.ok
        }
        return New-Check -Name $Name -Ok $innerOk -Message 'Command completed.' -Details $parsed
    }
    catch {
        return New-Check -Name $Name -Ok $false -Message $_.Exception.Message -Details @{ soft_fail = $SoftFail }
    }
}

function Get-CommandCheck {
    param([string]$Name, [bool]$Required)

    $command = Get-Command $Name -ErrorAction SilentlyContinue
    if ($command) {
        return New-Check -Name "runtime:$Name" -Ok $true -Message "$Name is available." -Details @{ source = $command.Source }
    }
    $message = if ($Required) { "$Name is required but was not found." } else { "$Name is optional and was not found." }
    return New-Check -Name "runtime:$Name" -Ok (-not $Required) -Message $message -Details @{ required = $Required }
}

$repoRoot = (Resolve-Path -LiteralPath $Root).Path
$checks = @()
$warnings = @()
$errors = @()
$filesWritten = @()

$extensionPath = Join-Path $repoRoot 'assetctl-extension.json'
if (Test-Path -LiteralPath $extensionPath -PathType Leaf) {
    $extension = Get-Content -Encoding UTF8 -LiteralPath $extensionPath -Raw | ConvertFrom-Json
    $checks += New-Check -Name 'extension-manifest' -Ok $true -Message 'assetctl-extension.json parsed.' -Details @{ version = $extension.version; default_mode = $extension.default_mode }
}
else {
    $checks += New-Check -Name 'extension-manifest' -Ok $false -Message 'assetctl-extension.json is missing.'
}

$checks += New-Check -Name 'runtime:powershell' -Ok ($PSVersionTable.PSVersion.Major -ge 5) -Message "PowerShell $($PSVersionTable.PSVersion) detected." -Details @{ version = "$($PSVersionTable.PSVersion)" }
$checks += Get-CommandCheck -Name 'python' -Required $true
$checks += Get-CommandCheck -Name 'git' -Required $false
$checks += Get-CommandCheck -Name 'node' -Required $false

$dirs = @(
    'reports',
    'reports\connector',
    '.assetctl',
    '.assetctl\requests',
    '.assetctl\cache'
)
foreach ($dir in $dirs) {
    $path = Join-Path $repoRoot $dir
    New-Item -ItemType Directory -Force -Path $path | Out-Null
    $filesWritten += $path
}

$placeholderPath = Join-Path $repoRoot '.assetctl\connector-config.placeholder.json'
$placeholder = [ordered]@{
    schema_version = '1.0'
    config_type = 'assetctl_connector_placeholder'
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    private_attach_required = $true
    private_attach_command = '.\tools\user-profile.ps1 -Operation authorize -AcceptNotice ...'
    note = 'This ignored placeholder contains no secrets and no private workspace path. User-authorized profiles are stored outside this repository.'
}
$encoding = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText($placeholderPath, ($placeholder | ConvertTo-Json -Depth 8) + [Environment]::NewLine, $encoding)
$filesWritten += $placeholderPath

if (-not $SkipUserProfileAutoAttach) {
    $profileStatus = Invoke-JsonCommand -Name 'user-profile-status' -FilePath (Join-Path $repoRoot 'tools\user-profile.ps1') -Parameters @{ Operation = 'status'; Root = $repoRoot; ProfileName = $ProfileName } -SoftFail $true
    if (-not $profileStatus.ok) {
        $warnings += "User profile status did not complete: $($profileStatus.message)"
        $profileStatus.ok = $true
    }
    $checks += $profileStatus

    $hasProfile = $false
    if ($profileStatus.details -and $profileStatus.details.outputs -and $profileStatus.details.outputs.profile_configured) {
        $hasProfile = [bool]$profileStatus.details.outputs.profile_configured
    }

    if ($hasProfile) {
        $profileAttach = Invoke-JsonCommand -Name 'user-profile-auto-attach' -FilePath (Join-Path $repoRoot 'tools\user-profile.ps1') -Parameters @{ Operation = 'attach'; Root = $repoRoot; ProfileName = $ProfileName } -SoftFail $true
        if (-not $profileAttach.ok) {
            $warnings += "User profile auto-attach did not complete: $($profileAttach.message)"
            $profileAttach.ok = $true
        }
        $checks += $profileAttach
    }
    else {
        $warnings += 'No user-authorized connector profile found; bootstrap will remain fixture-only.'
    }
}
else {
    $warnings += 'User profile auto-attach was skipped by -SkipUserProfileAutoAttach.'
}

if (-not $SkipValidation) {
    $checks += Invoke-JsonCommand -Name 'candidate-fixtures' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'validate-fixtures'; AssetsRoot = $repoRoot }
    $checks += Invoke-JsonCommand -Name 'connector-fixtures' -FilePath (Join-Path $repoRoot 'tools\connector-client.ps1') -Parameters @{ Operation = 'validate-fixtures'; Root = $repoRoot }
    $checks += Invoke-JsonCommand -Name 'public-leak-scan' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'leak-scan'; Path = $repoRoot }
    $checks += Invoke-JsonCommand -Name 'version' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'version' }
}
else {
    $warnings += 'Validation was skipped by -SkipValidation.'
}

if (-not $SkipUpdateCheck) {
    $updateCheck = Invoke-JsonCommand -Name 'update-check' -FilePath (Join-Path $repoRoot 'tools\candidate-gate.ps1') -Parameters @{ Operation = 'update-check' } -SoftFail $true
    if (-not $updateCheck.ok) {
        $warnings += "Update check did not complete: $($updateCheck.message)"
        $updateCheck.ok = $true
    }
    $checks += $updateCheck
}
else {
    $warnings += 'Update check was skipped by -SkipUpdateCheck.'
}

foreach ($check in $checks) {
    if (-not $check.ok) {
        $errors += "$($check.name): $($check.message)"
    }
}

$ok = ($errors.Count -eq 0)
$result = [ordered]@{
    ok = $ok
    operation_type = 'assetctl_public_bootstrap'
    schema_version = '1.0'
    root = $repoRoot
    generated_at_utc = [DateTime]::UtcNow.ToString('o')
    checks = $checks
    warnings = $warnings
    errors = $errors
    files_written = $filesWritten
    next_recommended_action = if ($ok) { 'Run .\tools\assetctl-doctor.ps1. For private access, run user-profile authorize only after the user allows connector access.' } else { 'Fix failed checks, then rerun bootstrap.' }
}

if ([string]::IsNullOrWhiteSpace($OutputPath)) {
    $OutputPath = Join-Path $repoRoot 'reports\bootstrap-latest.json'
}
$outputParent = Split-Path -Parent $OutputPath
if (-not [string]::IsNullOrWhiteSpace($outputParent)) {
    New-Item -ItemType Directory -Force -Path $outputParent | Out-Null
}
[System.IO.File]::WriteAllText($OutputPath, ($result | ConvertTo-Json -Depth 18) + [Environment]::NewLine, $encoding)

$result | ConvertTo-Json -Depth 18
if (-not $ok) {
    exit 1
}
