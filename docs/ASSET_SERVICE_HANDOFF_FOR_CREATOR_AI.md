# Asset Service Handoff For Asset-Consuming AI

This repository is the public-safe client for an asset service. It is not a PPT
generation system and it is not a raw asset dump.

Use it when your AI system, application, automation, or content pipeline needs
governed design assets. Websites and slide decks are examples, but the service
is not limited to them. The same connector pattern applies to reports,
dashboards, documents, apps, product UI, marketing material, education content,
internal tools, and any other output surface that needs assets selected under
the registry, license, risk, and media-boundary rules.

## Current Service Snapshot

The private backend has been refreshed for B37 template extraction and JPG
classification ingest. Public-safe summary:

```text
private backend repository: Kdreammaker/assets-management-system-for-ai
public client repository: Kdreammaker/ai-asset-contribution-gate
private backend branch: codex/b31-b-candidate-gate
latest backend closeout commits: 37e71e2, 42feeb2
promoted one-slide template references: 4,768
good template contracts: 3,567
template modules: 10,108
template compositions: 3,567
deck_component export items: 13,675
private metadata export items: 50,572
local vector index records: 38,236
metadata graph records: 38,236
```

Ten `template_pack_016` slide references remain unpromoted because no matching
JPG classification authority file exists for them.

This public snapshot is descriptive, not an entitlement to enumerate the private
backend. Public installs run against synthetic fixtures until the user
authorizes a local connector profile, scoped access-key identifier, or
controlled proxy metadata.

## What You Can Request

Ask the asset service for metadata-first recommendations:

```text
palette
icon
illustration
font
deck_component
```

For any asset-consuming system, request the assets you need by intent, audience,
tone, content domain, locale, medium, and output surface. Good requests are
specific, but they do not ask for private file paths or Drive IDs.

Example request intent:

```text
Korean capital market reform analyst briefing assets: KOSPI KOSDAQ index trend
deck components, finance chart modules, sober executive palette, timeline
icons, and Korean-friendly fonts.
```

## Install And Connect

Clone this public repository in the creator AI environment:

```powershell
git clone https://github.com/Kdreammaker/ai-asset-contribution-gate.git
cd ai-asset-contribution-gate
```

Validate the public client:

```powershell
.\tools\connector-client.ps1 -Operation validate-fixtures
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
```

If this PC or AI does not have the private repository connected, stay in the
public-only local workflow. Create a request and request bundle, then send only
the bundle to the private asset backend owner or approved handoff channel:

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "Korean capital market reform briefing finance timeline icons" -AssetTypes "icon" -DeliveryMode metadata_only -Limit 3 -OutputPath ".\reports\asset-service-request.json"
.\tools\connector-client.ps1 -Operation bundle-request -InputPath ".\reports\asset-service-request.json" -OutputPath ".\reports\asset-service-request-bundle.json"
.\tools\connector-client.ps1 -Operation validate-bundle -InputPath ".\reports\asset-service-request-bundle.json"
```

Invalid bundles are not written by default. If validation fails, revise the
request instead of sending the artifact. Unsafe-review/debug output requires
`-AllowInvalidOutput` and must stay clearly marked non-sendable.

When the private side returns a public-safe handoff response, validate it before
using the metadata:

```powershell
.\tools\connector-client.ps1 -Operation validate-handoff -InputPath ".\reports\asset-service-response-handoff.json"
```

Valid handoffs include metadata search success, deck-generation dry-run
success, safe rejection, and policy-blocked responses. Do not use a returned
handoff if validation reports private paths, Drive IDs, access-key secrets,
generated private reports, or raw asset leakage.

If private access is available, authorize and attach a connector profile. This
shows the connection notice, records a local audit event, and writes only
ignored local runtime config in this clone:

```powershell
.\tools\user-profile.ps1 -Operation authorize -ConnectorMode external-safe-proxy -ConnectorProxyUrl "<user-authorized-proxy-url>" -AccessKeyId "<key-id-only>" -AcceptNotice
.\tools\user-profile.ps1 -Operation attach
```

For local maintainer access, use `-ConnectorMode local-maintainer` with an
explicit user-authorized private workspace path. Attach creates
`.assetctl-private-connector.local.json` and `.assetctl/connection-guide.md`.
Those files are ignored by Git and must stay local. Do not give raw private
workspace paths to untrusted AIs; use a scoped connector or controlled proxy for
external callers.

## Asset-Consuming AI Workflow

1. Create a public-safe request in this repo.

```powershell
.\tools\connector-client.ps1 -Operation new-request -Query "Korean capital market reform finance timeline icons" -AssetTypes "icon" -DeliveryMode metadata_only -Limit 3 -OutputPath ".\reports\asset-service-request.json"
.\tools\connector-client.ps1 -Operation validate-request -InputPath ".\reports\asset-service-request.json"
```

For a PPT maker, prefer the narrow helper that creates separate public bundles
for fonts, color palettes, and deck components:

```powershell
.\tools\connector-client.ps1 -Operation ppt-metadata-bundles -Topic "Korean capital market reform executive presentation" -Limit 3 -OutputDir ".\reports\connector\ppt-metadata"
```

This helper is not a presentation preset. The PPT maker still assembles slides,
chooses the final theme, and handles font installation UX with user approval.
See `docs/PPT_MAKER_PUBLIC_ASSET_HANDOFF_GUIDE.md`.

2. Run real metadata search through the approved private backend boundary.

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-search -InputPath ".\downloaded-assets\connector\fixtures\asset-request.example.json"
```

For another PC, this private command runs on the private backend side after
receiving a public request bundle. The other PC should not clone the private
repo or receive private local paths.

3. Read the connector response. Internal maintainer responses may include raw
private identifiers. External-safe responses should consume:

```text
result_id
asset_type
name
license_class
license_action
risk_level
usage_groups
style_summary
policy_notes
media_policy_summary
materialization status
```

Do not ask the private backend to dump all records, enumerate categories, or
resolve guessed private IDs. Use specific design intents and continue from
server-issued `result_id` values when the backend requires them.

4. If binary files are needed, create a materialization proposal first.

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-materialize-plan -InputPath ".\downloaded-assets\connector\fixtures\asset-request.example.json"
.\downloaded-assets\tools\assetctl.ps1 connector-materialize-apply -DryRun
```

5. Only after approval, use the approved private export package manifest to map
exported files back to their source metadata.

```powershell
.\downloaded-assets\tools\assetctl.ps1 connector-materialize-apply -Approve
.\downloaded-assets\tools\assetctl.ps1 connector-build-ppt-export
```

Some private backends may expose output-specific export commands, such as a PPTX
package builder. Treat those as one export format, not as the identity of the
asset service.

## Copyright And Media Boundary

The asset service treats slide photos, embedded raster images, and JPG preview
files as non-reusable reference evidence. Do not extract, reuse, copy, or publish
those images as design assets.

Reusable design assets come from:

```text
shape/vector metadata derived from slide geometry
template module contracts
template composition contracts
approved open-source icons
approved open-font records
approved palette/design-token records
approved private export packages
```

Connector responses may include `template_media_policy`. Respect it. If a result
says embedded media is excluded or manifest-only, use the shape/vector/template
metadata and request an approved materialized package when needed.

## Public And Private Boundary

This public repository may contain:

```text
tools
schemas
synthetic fixtures
public-safe handoff docs
public-safe request examples
```

It must not contain:

```text
raw private assets
private registry exports
Google Drive IDs
local absolute paths
approval records
generated private reports
embedded slide photos or JPG previews as reusable assets
```

## Minimal Prompt For An Asset-Consuming AI

Use this prompt when handing the asset service to another AI:

```text
You are building or operating a system that needs governed design assets. Use
https://github.com/Kdreammaker/ai-asset-contribution-gate as the public-safe
asset-service client, not as an asset dump or generator. Read
docs/ASSET_SERVICE_HANDOFF_FOR_CREATOR_AI.md and docs/PRIVATE_WORKSPACE_CONNECTOR_SETUP.md.
Validate fixtures, create metadata-only asset requests with tools/connector-client.ps1,
create request bundles for other-PC handoff, and call the private backend
assetctl connector commands only from an authorized private workspace or
controlled proxy. Request palette, icon, illustration, font, and deck_component
assets by intent, domain, audience, medium, and output surface. PPT and website
requests are examples only. Do not copy private registry exports, Drive IDs,
approval records, raw assets, local paths, embedded slide photos, or JPG
previews into the public repo or generated output. Use connector metadata,
template_media_policy, license_action, risk_level, and approved package
manifests to decide what can be used.
```
