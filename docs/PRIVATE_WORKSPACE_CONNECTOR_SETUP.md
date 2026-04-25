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
absolute paths into the public repo. Use tools/setup-private-connector.ps1 with
the private workspace path only when I approve local maintainer access,
validate the connector, and use the private workspace assetctl commands for real
search, materialization proposals, and approved package export. For untrusted or
external agents, use a scoped connector, access key, or controlled proxy instead
of sharing the raw private workspace path.
```

## Setup Command

From the public toolkit root:

```powershell
.\tools\bootstrap-workspace.ps1
.\tools\assetctl-doctor.ps1
.\tools\setup-private-connector.ps1 -PrivateWorkspaceRoot "<owner-approved-private-workspace>" -CheckUpdates
```

`setup-private-connector.ps1` no longer guesses a sibling private workspace by
default. A local maintainer may opt in to sibling inference for their own
machine by passing `-AllowSiblingInference`, but automation should pass
`-PrivateWorkspaceRoot` explicitly.

For external or untrusted agents, use owner-provided proxy metadata instead of a
raw private path:

```powershell
.\tools\setup-private-connector.ps1 -ConnectorMode external-safe-proxy -ConnectorProxyUrl "<owner-provided-proxy-url>" -AccessKeyId "<key-id-only>" -CheckUpdates
```

Do not store access-key secrets in this repo. `AccessKeyId` is an identifier,
not the secret value.

The setup command writes an ignored local file:

```text
.assetctl-private-connector.local.json
```

That file may contain local absolute paths and must remain untracked.

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
```

## Normal AI Workflow

Create a public-safe request:

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "Korean capital market reform briefing assets: KOSPI KOSDAQ finance chart modules, timeline icons, executive palette, Korean fonts" -AssetTypes "palette,icon,deck_component,font" -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\connector-request.json"
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
