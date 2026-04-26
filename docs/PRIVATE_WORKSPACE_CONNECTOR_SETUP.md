# Private Workspace Connector Setup

This public toolkit is safe to install in a new AI workspace, but it does not
contain real asset binaries, private registry exports, Drive linkage, approval
records, or local machine paths.

To use the real asset library, connect this public toolkit to a private
workspace that owns the asset registry and connector runtime.

Public installs are fixture-only by default. A public request file is not an
access grant, and a request-body `trust_tier` value is not authoritative. The
private backend, a scoped access key, or a controlled proxy must assign the
effective connector boundary.

## AI Install Prompt

Give a new AI agent this instruction:

```text
Install the public AI asset toolkit, then connect it to my private asset
workspace using the public repo instructions. Do not copy private registry
files, raw assets, Drive IDs, approval records, generated reports, or local
absolute paths into the public repo. Use tools/user-profile.ps1 to show the
connection notice, collect my connection approval, record a local audit event,
and attach only through ignored local runtime config. Use a local private
workspace path only when I approve local maintainer access. For untrusted or
external agents, use a scoped connector, access-key identifier, or controlled
proxy instead of sharing the raw private workspace path.
```

## Setup Command

From the public toolkit root:

```powershell
.\tools\bootstrap-workspace.ps1
.\tools\assetctl-doctor.ps1
.\tools\user-profile.ps1 -Operation authorize -ConnectorMode external-safe-proxy -ConnectorProxyUrl "<user-authorized-proxy-url>" -AccessKeyId "<key-id-only>" -AcceptNotice
.\tools\user-profile.ps1 -Operation attach
```

`user-profile.ps1 -Operation authorize` returns the pre-connection notice in
JSON. `-AcceptNotice` means the user has allowed this connector profile for the
current machine/session. Authorization writes the profile outside this
repository and records a user-local audit event. Attach writes only ignored
local runtime files in this clone.

For a local maintainer who is allowed to connect a local private workspace path:

```powershell
.\tools\user-profile.ps1 -Operation authorize -ConnectorMode local-maintainer -PrivateWorkspaceRoot "<user-authorized-private-workspace>" -AcceptNotice
.\tools\user-profile.ps1 -Operation attach
```

Bootstrap checks for an existing user-authorized profile and auto-attaches it
unless `-SkipUserProfileAutoAttach` is supplied. `setup-private-connector.ps1`
remains as a lower-level command for controlled automation. It no longer guesses
a sibling private workspace by default. A local maintainer may opt in to sibling
inference for their own machine by passing `-AllowSiblingInference`, but
automation should prefer `user-profile.ps1`.

Do not store access-key secrets in this repo. `AccessKeyId` is an identifier,
not the secret value.

The setup command writes an ignored local file:

```text
.assetctl-private-connector.local.json
.assetctl/connection-guide.md
```

Those files may contain local runtime hints and must remain untracked. The
user-authorized profile and connection audit log are stored outside this
repository under the user's local AssetCtl config location.

## Other-PC Public-Only Handoff

A different PC or AI is not expected to have the private repository connected.
For that environment, do not authorize a local maintainer path unless the
private workspace is actually present and the user approves that local access.

Use a public-only request bundle instead:

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "Korean capital market reform finance timeline icons" -AssetTypes "icon" -Limit 3 -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation bundle-request -InputPath ".\reports\connector-request.json" -OutputPath ".\reports\connector-request-bundle.json"
.\tools\connector-client.ps1 -Operation validate-bundle -InputPath ".\reports\connector-request-bundle.json"
```

Invalid bundles are not written by default. If a bundle fails validation, do
not send it to the private backend unless it was intentionally created with
`-AllowInvalidOutput` for an unsafe-review/debug path and clearly marked
non-sendable.

The private backend owner processes that bundle and returns a public-safe
handoff JSON. Validate the returned file locally:

```powershell
.\tools\connector-client.ps1 -Operation validate-handoff -InputPath ".\reports\connector-response-handoff.json"
```

The returned handoff can be a success, safe rejection, or policy-blocked
response. Validation must fail if it contains private workspace paths, Drive
IDs, access-key secrets, generated private reports, or raw asset payloads.

For the current owner machine only, an explicitly attached `local-maintainer`
profile can use the convenience runner:

```powershell
.\tools\invoke-private-connector.ps1 -Operation search -InputPath ".\reports\connector-request.json"
```

This runner is not the other-PC default and refuses non-local-maintainer
profiles.

## What Setup Verifies

The setup command checks:

```text
public connector fixtures parse and validate
private downloaded-assets/tools/assetctl.ps1 exists
private downloaded-assets/registry/asset-registry.jsonl exists
private downloaded-assets/connector/schemas exists
private connector-capabilities runs, unless -SkipPrivateValidation is used
private paths are redacted from setup and doctor output by default
```

It does not:

```text
copy private assets into the public repo
copy private registry exports into the public repo
fetch Drive binaries
approve materialization proposals
mutate Google Drive
publish generated reports
clone or fetch the private repository
guess local private workspace paths unless -AllowSiblingInference is supplied
store access-key secrets
```

## Normal AI Workflow

Create a public-safe request:

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "Korean capital market reform finance timeline icons" -AssetTypes "icon" -Limit 3 -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\connector-request.json"
```

PPT makers should use separate low-limit metadata requests for fonts, palettes,
and deck components, or the helper:

```powershell
.\tools\connector-client.ps1 -Operation ppt-metadata-bundles -Topic "Korean business executive KPI presentation" -Limit 3 -OutputDir ".\reports\connector\ppt-metadata"
```

Run real metadata search in the private workspace:

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-search -InputPath ".\downloaded-assets\connector\fixtures\asset-request.example.json"
```

Broad "all assets", empty browse, dump/export-everything, and systematic
enumeration requests should be rejected or throttled by the private backend.
Use specific design intents and server-issued result identifiers for follow-up
resolve/materialization flows when the backend requires them.

For binary use, generate a proposal first:

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-materialize-plan -InputPath ".\downloaded-assets\connector\fixtures\asset-request.example.json"
.\downloaded-assets\tools\assetctl.ps1 connector-materialize-apply -DryRun
```

Approved export remains private-workspace owned:

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-materialize-apply -Approve
.\downloaded-assets\tools\assetctl.ps1 connector-build-ppt-export
```

## How AI Knows Which Asset Was Used

After approved materialization, the private workspace writes an ignored package
manifest under:

```text
downloaded-assets/_work/connector-packages/latest/connector-package-manifest.json
```

The manifest maps every exported file back to:

```text
asset_uid
source_name
asset_type
license_class
license_action
risk_level
relative registry path
sha256
size_bytes
```

AI agents should read that manifest before claiming which assets were used.
Do not publish the manifest, raw private IDs, local paths, Drive IDs, or package
evidence back into this public repository.

## Public And Private Boundary

The public repo is the reusable client and safety contract.

The private workspace is the asset backend. It owns:

```text
real registry data
raw assets
Drive-backed cache verification
approval records
package manifests
PPTX and other generated exports
graphify and local vector results over private metadata
```

This split lets public AI agents install the same safe toolkit while keeping
private asset evidence and binaries out of the public repository.
