# PPT Maker Public Asset Handoff Guide

This guide is for a PPT maker, slide-generation agent, or presentation
assistant that wants to request assets from the public asset toolkit without
gaining access to the private asset repository.

The public toolkit is a communication device. It creates public-safe request
bundles, validates returned handoffs, and consumes only redacted metadata or
approved packages. It must not be treated as a private repository access path.

## Handoff Packet For A PPT Maker AI

Give this section to the PPT maker AI that is building the presentation:

```text
Use the public asset toolkit only. Do not clone, install, or request access to
the private asset repository.

Your job:
1. Create narrow public request bundles for the assets you need.
2. Send those bundles through the approved handoff channel to the asset service
   owner.
3. Validate the returned public handoff files.
4. Use the returned metadata to choose fonts, palettes, layout/deck component
   direction, and any slide-specific visual assets.
5. Assemble the PPT yourself.

The asset service can return public-safe metadata, opaque result_id values,
license/policy notes, and approved package handoffs when separately approved.
It can recommend and, through an approved package/materialization flow, provide
approved files for icons, vector illustrations, fonts, and other explicitly
approved visual assets. It does not return private paths, Drive IDs, private
registry dumps, generated private reports, or raw unapproved assets.
```

Minimum public-only setup:

```powershell
git clone https://github.com/Kdreammaker/ai-asset-contribution-gate.git assetctl-public-toolkit
cd assetctl-public-toolkit
git checkout v0.3.8
.\tools\bootstrap-workspace.ps1
.\tools\assetctl-doctor.ps1 -SkipNetwork
```

Generate the recommended PPT metadata request bundles:

```powershell
.\tools\connector-client.ps1 -Operation ppt-metadata-bundles `
  -Topic "Korean business executive KPI presentation" `
  -Limit 3 `
  -OutputDir ".\reports\connector\ppt-metadata"
```

Send only these public bundle files to the asset service owner:

```text
reports/connector/ppt-metadata/ppt-assets-fonts-bundle.json
reports/connector/ppt-metadata/ppt-assets-palettes-bundle.json
reports/connector/ppt-metadata/ppt-assets-layouts-bundle.json
```

These three bundles are the recommended starting set, not the full capability
surface. For slide-specific visuals, create additional narrow request bundles
with `new-request` and `bundle-request`.

```powershell
.\tools\connector-client.ps1 -Operation new-request `
  -Query "KPI risk warning icon for executive dashboard slide" `
  -AssetTypes "icon" `
  -DeliveryMode metadata_only `
  -Limit 3 `
  -OutputPath ".\reports\connector\ppt-risk-icons-request.json"

.\tools\connector-client.ps1 -Operation bundle-request `
  -InputPath ".\reports\connector\ppt-risk-icons-request.json" `
  -OutputPath ".\reports\connector\ppt-risk-icons-bundle.json"

.\tools\connector-client.ps1 -Operation validate-bundle `
  -InputPath ".\reports\connector\ppt-risk-icons-bundle.json"
```

Use the same pattern for a specific illustration, approved photo/image need, or
mockup need. Keep each query specific and low-limit.

After the owner returns handoff JSON files, validate each one:

```powershell
.\tools\connector-client.ps1 -Operation validate-handoff -InputPath <returned-handoff.json>
```

If validation passes, read `response.results` and use the returned
`display_name`, `asset_type`, `license_action`, `risk_level`, `recommended_for`,
`avoid_for`, `style_summary`, `policy_notes`, and `materialization` fields. If
validation fails, do not use the handoff.

## Recommended Request Shape

Request narrow metadata groups instead of asking for all available assets:

```text
1. presentation fonts
2. color palettes
3. slide layout or deck components
4. icons for a specific slide concept or UI metaphor
5. vector illustrations for a specific scene
6. approved photos, images, or mockups only for a specific use case and only
   when the owner-side service returns them as allowed candidates
```

Use low limits. A limit of 3 to 5 per group is usually enough for a slide agent
to choose a coherent direction. Broad, empty, dump, all-assets, or systematic
enumeration requests are expected to be rejected.

The public helper creates the three common PPT metadata bundles:

```powershell
.\tools\connector-client.ps1 -Operation ppt-metadata-bundles `
  -Topic "Korean business executive KPI presentation" `
  -Limit 3 `
  -OutputDir ".\reports\connector\ppt-metadata"
```

The helper writes separate request and bundle files for fonts, palettes, and
deck components. It is not a design preset and does not assemble slides.

The helper is the preferred path for normal PPT maker onboarding. Use manual
`new-request` plus `bundle-request` commands only when the PPT needs an
additional specific asset category, such as a small icon set, one vector
illustration direction, an approved photo/image candidate, or a mockup.

Do not ask for an exhaustive asset list. The safe substitute for a list is a
capability summary plus narrow candidate shortlists. Supported request types
may include:

```text
font
palette
deck_component
icon
illustration
photo or image, when the owner-side service marks the result safe for the
requested use case
mockup, when available and policy-allowed
```

## What The Asset Service Can Return

The owner-side private backend may return a public-safe handoff containing:

```text
metadata-only recommendations
opaque result_id values
display names
asset type
license_class and license_action
risk_level
usage groups
recommended_for and avoid_for notes
style and audience summaries
public-safe materialization status
policy notes
```

For approved package flows, the private owner-side backend may return:

```text
an approved package manifest
approved asset files
license files or license references required for the package
checksums
installation or import instructions
```

Approved packages are a separate flow from metadata search. The PPT maker
should not expect raw font files, raw icons, image binaries, local private
paths, Drive IDs, or private registry records from ordinary metadata search.

When a returned metadata result is useful, the PPT maker may ask for an approved
package/materialization flow by `result_id`. Approved packages may contain files
such as:

```text
font files with license files
SVG icon files
SVG or other approved vector illustration files
approved raster image/photo files when license and source policy permit them
manifest and checksum files
usage or installation instructions
```

Package approval is owner-side. A metadata result does not automatically grant
file access.

## What The PPT Maker Must Do

The PPT maker is responsible for:

```text
choosing the final design direction
combining font, palette, and layout metadata into a presentation theme
building slides
checking whether required fonts are already installed
asking the user before installing fonts or changing the local machine
falling back gracefully when a font cannot be installed
respecting license_action and policy_notes in the returned handoff
requesting approved packages by result_id only when actual files are needed
```

The asset service should not assemble a full presentation preset unless a
separate product contract explicitly asks for that.

## Font Package And Installation UX

Fonts are only useful to the PPT maker if they can be used by PowerPoint or the
slide rendering environment. Use this staged UX:

```text
1. Request font metadata.
2. Select a font result_id.
3. Request an approved font package or materialization plan.
4. Validate the returned handoff/package manifest.
5. Check whether the font is already installed.
6. Ask the user for explicit approval before installing.
7. If the AI/app can install fonts, perform a user-scope install and verify.
8. If the AI/app cannot install fonts, show the package folder path and clear
   manual install instructions.
9. If installation fails, use a safe fallback font and record the fallback.
```

Font installation must not happen as an automatic side effect of metadata
search. It changes the user's local environment and may require license review,
package integrity checks, and explicit consent.

## What Not To Request

Do not request:

```text
all assets
raw registry dumps
private workspace paths
Drive file IDs or Drive links
access-key secrets
private reports
raw unapproved binaries
systematic category browsing
trust_tier overrides
```

Do not put private-only field names or secrets in free-text queries. Examples:

```text
access_key_secret
client_secret
private_workspace_root
private Drive file identifier fields
local_path
trust_tier
```

## User Identity And Abuse Controls

For quota control and abuse blocking, the service needs a stable requester
subject. The preferred design is:

```text
server-issued access_key_id or public_user_id
server-side quota and abuse tracking by key_id
public profile stores only key IDs, never secret values
private backend assigns trust_tier; public requests cannot claim it
```

Do not rely on a user-supplied ID as the only control. A malicious requester can
change it.

Avoid using raw PC identifiers or raw IP addresses as durable identity. Even if
hashed, device and IP fingerprints can still be personal or pseudonymous data
because they are intended to single out a user or machine. If a hosted relay is
introduced later, IP-derived signals may be used for short-lived rate limiting
with a server-side secret HMAC and retention limits. They should be abuse
signals, not primary user identity.

Supabase is not required for file-based Phase 1. It is one possible later
hosted option. Other valid designs include Cloudflare Workers with KV/D1,
signed access keys, or another owner-controlled relay.

## Validation

Validate every artifact at each boundary:

```powershell
.\tools\connector-client.ps1 -Operation validate-bundle -InputPath <bundle.json>
.\tools\connector-client.ps1 -Operation validate-handoff -InputPath <handoff.json>
```

If validation fails, do not use the handoff. Ask the private owner-side backend
for a corrected public-safe response.
