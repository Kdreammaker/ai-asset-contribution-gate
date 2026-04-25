param(
    [ValidateSet('status', 'authorize', 'attach', 'revoke', 'show-guide')]
    [string]$Operation = 'status',
    [string]$Root = (Resolve-Path (Join-Path $PSScriptRoot '..')).Path,
    [string]$ProfileName = 'default',
    [ValidateSet('local-maintainer', 'external-safe-proxy')]
    [string]$ConnectorMode = 'external-safe-proxy',
    [string]$PrivateWorkspaceRoot = '',
    [string]$ConnectorProxyUrl = '',
    [string]$AccessKeyId = '',
    [switch]$AcceptNotice,
    [switch]$ShowPrivatePaths
)

$ErrorActionPreference = 'Stop'

try {
    [Console]::OutputEncoding = New-Object System.Text.UTF8Encoding($false)
    $OutputEncoding = [Console]::OutputEncoding
}
catch {
}

function Get-ProfileBase {
    if (-not [string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) {
        return (Join-Path $env:LOCALAPPDATA 'AssetCtl')
    }
    if (-not [string]::IsNullOrWhiteSpace($env:HOME)) {
        return (Join-Path $env:HOME '.assetctl')
    }
    return (Join-Path ([System.IO.Path]::GetTempPath()) 'AssetCtl')
}

function Get-SafeProfileName {
    param([string]$Name)
    $safe = ([string]$Name).Trim()
    if ([string]::IsNullOrWhiteSpace($safe)) { $safe = 'default' }
    return ($safe -replace '[^A-Za-z0-9_.-]', '-')
}

function Protect-Value {
    param([string]$Value, [string]$Label)
    if ($ShowPrivatePaths) { return $Value }
    if ([string]::IsNullOrWhiteSpace($Value)) { return '' }
    return "[redacted:$Label]"
}

function Test-AccessKeyIdLooksSecret {
    param([string]$Value)
    if ([string]::IsNullOrWhiteSpace($Value)) { return $false }
    if ($Value -match '^(sk-|xox|ghp_|github_pat_|glpat-|AKIA)') { return $true }
    if ($Value -match '^[A-Fa-f0-9]{32,}$') { return $true }
    if ($Value.Length -gt 128) { return $true }
    return $false
}

function Write-Utf8File {
    param([string]$Path, [string]$Text)
    $parent = Split-Path -Parent $Path
    if (-not [string]::IsNullOrWhiteSpace($parent)) {
        New-Item -ItemType Directory -Force -Path $parent | Out-Null
    }
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::WriteAllText($Path, $Text, $encoding)
}

function Add-AuditEvent {
    param([string]$AuditPath, [hashtable]$Event)
    $parent = Split-Path -Parent $AuditPath
    New-Item -ItemType Directory -Force -Path $parent | Out-Null
    $encoding = New-Object System.Text.UTF8Encoding($false)
    [System.IO.File]::AppendAllText($AuditPath, (($Event | ConvertTo-Json -Depth 12 -Compress) + [Environment]::NewLine), $encoding)
}

function New-Notice {
    return [ordered]@{
        title = 'User-authorized asset connector profile'
        summary = 'This connects the public toolkit to a user-authorized connector profile on this machine.'
        before_you_accept = @(
            'The public toolkit remains fixture-only unless a user-authorized profile is present.',
            'The profile may point to a private local backend or to controlled proxy metadata.',
            'The public toolkit does not auto-clone private repositories and does not guess private paths by default.',
            'Access-key secret values must not be stored here; only key IDs or proxy metadata are allowed.',
            'Connection events are logged to a user-local audit log outside this repository.'
        )
        allowed_after_connection = @(
            'create and validate public-safe connector requests',
            'run metadata search through an authorized local backend or controlled proxy',
            'prepare materialization/export proposals through the private backend boundary'
        )
        not_allowed = @(
            'copy private registry exports into this public repo',
            'copy raw assets into this public repo',
            'print Drive IDs, access-key secrets, or private local paths in tracked docs',
            'bypass private approval gates for binary materialization'
        )
        consent = 'Run authorize with -AcceptNotice only after the user allows this connector profile for this machine/session.'
    }
}

function New-GuideText {
    param([string]$Mode, [string]$Profile, [string]$GeneratedAt)
    return @"
# AssetCtl Connection Guide

Generated: $GeneratedAt
Profile: $Profile
Mode: $Mode

## What Is Connected

This public toolkit is connected through a user-authorized local profile. The
profile is stored outside this repository. This repository keeps only ignored
local runtime/config files.

## Safe Default Use

Create a public-safe request:

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "dashboard security icon" -AssetTypes "icon" -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\connector-request.json"
```

Then send the request through the user-authorized backend or proxy. Do not copy
private registry exports, Drive IDs, raw assets, or access-key secrets into this
public repository.

## Audit

Connection authorization and attach events are recorded in the user-local
AssetCtl audit log outside this repository.
"@
}

$repoRoot = (Resolve-Path -LiteralPath $Root).Path
$safeProfileName = Get-SafeProfileName -Name $ProfileName
$profileBase = Get-ProfileBase
$profileDir = Join-Path $profileBase 'profiles'
$profilePath = Join-Path $profileDir "$safeProfileName.connector-profile.json"
$auditPath = Join-Path (Join-Path $profileBase 'audit') 'connector-audit.jsonl'
$guidePath = Join-Path $repoRoot '.assetctl\connection-guide.md'
$notice = New-Notice
$warnings = @()
$errors = @()
$filesRead = @()
$filesWritten = @()
$outputs = [ordered]@{
    profile_name = $safeProfileName
    profile_configured = (Test-Path -LiteralPath $profilePath -PathType Leaf)
    profile_path = Protect-Value -Value $profilePath -Label 'user_profile_path'
    audit_log = Protect-Value -Value $auditPath -Label 'user_audit_log'
    local_connector_config = '.assetctl-private-connector.local.json'
}

if ($Operation -eq 'status') {
    if (Test-Path -LiteralPath $profilePath -PathType Leaf) {
        $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath | ConvertFrom-Json
        $outputs.profile_configured = $true
        $outputs.connector_mode = $profile.connector_mode
        $outputs.user_authorized = [bool]$profile.user_authorized
        $outputs.private_workspace_root = Protect-Value -Value $profile.private_workspace_root -Label 'private_workspace_root'
        $outputs.connector_proxy_url = if ($profile.connector_proxy_url) { '[configured]' } else { '' }
        $outputs.access_key_id = if ($profile.access_key_id) { '[configured]' } else { '' }
        $filesRead += (Protect-Value -Value $profilePath -Label 'user_profile_path')
    }
}
elseif ($Operation -eq 'show-guide') {
    $outputs.notice = $notice
    if (Test-Path -LiteralPath $guidePath -PathType Leaf) {
        $outputs.guide_path = '.assetctl/connection-guide.md'
        $outputs.guide_text = Get-Content -Raw -Encoding UTF8 -LiteralPath $guidePath
        $filesRead += '.assetctl/connection-guide.md'
    }
    else {
        $outputs.guide_text = New-GuideText -Mode 'not_configured' -Profile $safeProfileName -GeneratedAt ([DateTime]::UtcNow.ToString('o'))
    }
}
elseif ($Operation -eq 'authorize') {
    if (-not $AcceptNotice) { $errors += 'User authorization requires -AcceptNotice after reviewing the connection notice.' }
    if ($ConnectorMode -eq 'local-maintainer' -and [string]::IsNullOrWhiteSpace($PrivateWorkspaceRoot)) {
        $errors += 'local-maintainer authorization requires -PrivateWorkspaceRoot supplied by the user.'
    }
    if ($ConnectorMode -eq 'external-safe-proxy' -and [string]::IsNullOrWhiteSpace($ConnectorProxyUrl) -and [string]::IsNullOrWhiteSpace($AccessKeyId)) {
        $errors += 'external-safe-proxy authorization requires -ConnectorProxyUrl or -AccessKeyId metadata.'
    }
    if (Test-AccessKeyIdLooksSecret -Value $AccessKeyId) {
        $errors += 'AccessKeyId looks like a secret token. Store only a non-secret key identifier here.'
    }
    if ($errors.Count -eq 0) {
        $privateRoot = ''
        if ($ConnectorMode -eq 'local-maintainer') {
            $privateRoot = (Resolve-Path -LiteralPath $PrivateWorkspaceRoot -ErrorAction Stop).Path
        }
        $profile = [ordered]@{
            schema_version = '1.0'
            profile_type = 'assetctl_user_authorized_connector_profile'
            profile_name = $safeProfileName
            connector_mode = $ConnectorMode
            user_authorized = $true
            authorized_at_utc = [DateTime]::UtcNow.ToString('o')
            private_workspace_root = $privateRoot
            connector_proxy_url = $ConnectorProxyUrl
            access_key_id = $AccessKeyId
            access_key_secret_storage = 'not_stored_by_public_toolkit'
            safety = [ordered]@{
                private_repo_auto_clone = $false
                private_path_guessing_by_default = $false
                access_key_secret_persisted = $false
                public_repo_receives_private_registry = $false
                public_repo_receives_raw_assets = $false
            }
        }
        Write-Utf8File -Path $profilePath -Text (($profile | ConvertTo-Json -Depth 12) + [Environment]::NewLine)
        $filesWritten += (Protect-Value -Value $profilePath -Label 'user_profile_path')
        Add-AuditEvent -AuditPath $auditPath -Event @{
            event_type = 'profile_authorized'
            profile_name = $safeProfileName
            connector_mode = $ConnectorMode
            generated_at_utc = [DateTime]::UtcNow.ToString('o')
            public_toolkit_root = '[redacted:public_toolkit_root]'
            access_key_secret_persisted = $false
        }
        $filesWritten += (Protect-Value -Value $auditPath -Label 'user_audit_log')
        $outputs.profile_configured = $true
        $outputs.connector_mode = $ConnectorMode
        $outputs.user_authorized = $true
        $outputs.private_workspace_root = Protect-Value -Value $privateRoot -Label 'private_workspace_root'
        $outputs.connector_proxy_url = if ($ConnectorProxyUrl) { '[configured]' } else { '' }
        $outputs.access_key_id = if ($AccessKeyId) { '[configured]' } else { '' }
    }
}
elseif ($Operation -eq 'attach') {
    if (-not (Test-Path -LiteralPath $profilePath -PathType Leaf)) {
        $errors += 'No user-authorized connector profile found. Run authorize first.'
    }
    else {
        $profile = Get-Content -Raw -Encoding UTF8 -LiteralPath $profilePath | ConvertFrom-Json
        $filesRead += (Protect-Value -Value $profilePath -Label 'user_profile_path')
        if (-not [bool]$profile.user_authorized) { $errors += 'Connector profile is present but not user-authorized.' }
        if ($errors.Count -eq 0) {
            $setupParams = @{ ConnectorMode = $profile.connector_mode }
            if ($profile.connector_mode -eq 'local-maintainer') {
                $setupParams.PrivateWorkspaceRoot = $profile.private_workspace_root
            }
            else {
                if ($profile.connector_proxy_url) { $setupParams.ConnectorProxyUrl = $profile.connector_proxy_url }
                if ($profile.access_key_id) { $setupParams.AccessKeyId = $profile.access_key_id }
            }
            $setupText = & (Join-Path $PSScriptRoot 'setup-private-connector.ps1') @setupParams 2>&1
            $setupSucceeded = $?
            $setupExit = 0
            if ($null -ne $LASTEXITCODE -and -not [string]::IsNullOrWhiteSpace([string]$LASTEXITCODE)) {
                $setupExit = [int]$LASTEXITCODE
            }
            elseif (-not $setupSucceeded) {
                $setupExit = 1
            }
            $setupJoined = ($setupText -join [Environment]::NewLine).Trim()
            $setupParsed = $null
            if (-not [string]::IsNullOrWhiteSpace($setupJoined)) { $setupParsed = $setupJoined | ConvertFrom-Json }
            if ($setupExit -ne 0 -or ($setupParsed -and -not [bool]$setupParsed.ok)) {
                $errors += 'Profile attach failed through setup-private-connector.'
            }
            $outputs.attach_result = $setupParsed
            if ($errors.Count -eq 0) {
                $guide = New-GuideText -Mode $profile.connector_mode -Profile $safeProfileName -GeneratedAt ([DateTime]::UtcNow.ToString('o'))
                Write-Utf8File -Path $guidePath -Text $guide
                $filesWritten += '.assetctl/connection-guide.md'
                $outputs.guide_path = '.assetctl/connection-guide.md'
                $outputs.window_summary = 'Connected through a user-authorized profile. Read .assetctl/connection-guide.md for safe next steps.'
            }
            Add-AuditEvent -AuditPath $auditPath -Event @{
                event_type = 'profile_attached'
                profile_name = $safeProfileName
                connector_mode = $profile.connector_mode
                generated_at_utc = [DateTime]::UtcNow.ToString('o')
                attach_ok = ($errors.Count -eq 0)
                access_key_secret_persisted = $false
            }
            $filesWritten += (Protect-Value -Value $auditPath -Label 'user_audit_log')
        }
    }
}
elseif ($Operation -eq 'revoke') {
    if (Test-Path -LiteralPath $profilePath -PathType Leaf) {
        Remove-Item -LiteralPath $profilePath -Force
        Add-AuditEvent -AuditPath $auditPath -Event @{
            event_type = 'profile_revoked'
            profile_name = $safeProfileName
            generated_at_utc = [DateTime]::UtcNow.ToString('o')
        }
        $filesWritten += (Protect-Value -Value $auditPath -Label 'user_audit_log')
    }
    $outputs.profile_configured = $false
}

$ok = ($errors.Count -eq 0)
if ($ok) {
    if ($Operation -eq 'authorize') {
        $next = 'Run .\tools\user-profile.ps1 -Operation attach to connect this clone, or rerun bootstrap to auto-attach the authorized profile.'
    }
    elseif ($Operation -eq 'attach') {
        $next = 'Read .assetctl/connection-guide.md, then create a public-safe connector request.'
    }
    elseif ($Operation -eq 'status' -and -not $outputs.profile_configured) {
        $next = 'Run authorize with -AcceptNotice after the user allows connector access.'
    }
    else {
        $next = 'Continue with bootstrap, doctor, or connector-client commands.'
    }
}
else {
    $next = 'Review the notice and errors, then rerun with explicit user authorization.'
}

$result = [ordered]@{
    ok = $ok
    operation_type = "user_profile_$Operation"
    schema_version = '1.0'
    notice = $notice
    outputs = $outputs
    warnings = @($warnings)
    errors = @($errors)
    files_read = @($filesRead)
    files_written = @($filesWritten)
    next_recommended_action = $next
}

$result | ConvertTo-Json -Depth 18
if (-not $ok) { exit 1 }
