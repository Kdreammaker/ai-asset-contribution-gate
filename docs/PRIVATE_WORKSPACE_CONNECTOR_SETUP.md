# Private Workspace Connector Setup

This public toolkit is safe to install in a new AI workspace, but it does not
contain real asset binaries, private registry exports, Drive linkage, approval
records, or local machine paths.

To use the real asset library, connect this public toolkit to a private
workspace that owns the asset registry and connector runtime.

## AI Install Prompt

Give a new AI agent this instruction:

```text
Install the public AI asset toolkit, then connect it to my private asset
workspace using the public repo instructions. Do not copy private registry
files, raw assets, Drive IDs, approval records, generated reports, or local
absolute paths into the public repo. Use tools/setup-private-connector.ps1 with
the private workspace path, validate the connector, and use the private
workspace assetctl commands for real search, materialization proposals, and
approved package export.
```

## Setup Command

From the public toolkit root:

```powershell
.\tools\setup-private-connector.ps1 -PrivateWorkspaceRoot "<path-to-private-workspace>"
```

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
```

It does not:

```text
copy private assets into the public repo
copy private registry exports into the public repo
fetch Drive binaries
approve materialization proposals
mutate Google Drive
publish generated reports
```

## Normal AI Workflow

Create a public-safe request:

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "Korean B2B pitch deck calm blue KPI" -AssetTypes "palette,icon,deck_component" -OutputPath ".\reports\connector-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\connector-request.json"
```

Run real metadata search in the private workspace:

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-search -InputPath ".\downloaded-assets\connector\fixtures\asset-request.example.json"
```

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
