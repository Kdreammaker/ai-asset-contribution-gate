# PPT Maker Public Asset Handoff Guide

This guide is for a PPT maker, slide-generation agent, or presentation
assistant that wants to request assets from the public asset toolkit without
gaining access to the private asset repository.

The public toolkit is a communication device. It creates public-safe request
bundles, validates returned handoffs, and consumes only redacted metadata or
approved packages. It must not be treated as a private repository access path.

## Recommended Request Shape

Request narrow metadata groups instead of asking for all available assets:

```text
1. presentation fonts
2. color palettes
3. slide layout or deck components
4. optional icons or illustrations for a specific visual need
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
should not expect raw font files, raw icons, local private paths, Drive IDs, or
private registry records from ordinary metadata search.

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
