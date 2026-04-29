# Asset System Consumer Integration Guide

This guide defines the public-safe contract for any third-party consumer that
requests governed assets from the asset system and later reports what it used.
The consumer may be a website builder, document generator, design or canvas
tool, ad/banner renderer, storyboard system, presentation renderer, or another
asset-consuming workflow.

The public toolkit is a communication device. It creates and validates
public-safe request bundles and validates returned public-safe responses. It is
not a private repository access path and it is not an asset dump.

PPT Maker is a tested reference consumer for the current B44 fixtures. It is
not the shape of the contract.

## Public And Private Boundary

The public side may receive public-safe metadata, opaque result IDs, stable
public reference keys, approval/package status, relative package paths after
approval, checksums, file sizes, license and policy notes, and returned
consumer reports.

The public side must not receive or publish:

```text
private paths
Drive IDs or Drive links
raw private registry rows or dumps
generated private reports
secrets, access keys, or token values
raw unapproved assets
raw source images that were not explicitly approved for the package
```

Package paths in public artifacts must be relative to the approved package
root. A local absolute path may exist inside a consumer runtime, but it must not
be copied into request bundles, package responses, returned reports, docs, or
fixtures.

## Consumer-Neutral Flow

The file-based integration flow is:

```text
1. Discovery request
   The consumer asks for candidates by intent, asset type, audience, locale,
   output surface, and delivery need.

2. Package or proposal request
   The consumer asks for a proposal or approved package for selected public
   result IDs or stable reference keys.

3. Approved package response
   The private backend returns only public-safe package metadata and, after
   approval, package files referenced by relative paths with checksums and file
   sizes.

4. Consumer build, render, or use step
   The consumer validates the package response, copies or resolves the
   approved files locally, uses only manifest assets, and records slot-level
   evidence or blocking fallback events.

5. Returned report validation
   The consumer returns final QA and used-assets evidence. Validators compare
   the returned report with the exact approved package response used by that
   output.
```

The flow is intentionally file-based. It does not require Cloudflare, Supabase,
hosted databases, public object storage, hosted queues, or direct public access
to the private backend.

## Approved Package Consumption Contract

Use these terms consistently:

```text
approved package
  The public-safe package response and file bundle approved by the private
  backend for a specific request.

use slot or asset slot
  A declared intended use location in the consumer output. A slot may represent
  a page hero image, card icon, document figure, canvas layer, slide visual, ad
  product shot, storyboard frame, or similar output-specific placement.

approved_asset_ref
  The slot's public-safe reference to the approved package asset that should be
  used for that slot.

manifest asset
  An entry in package_manifest.assets[] with relative_package_path, sha256,
  size_bytes, media_type, and license reference.

file-backed approved ref
  An approved_asset_ref that resolves to a manifest asset file in the approved
  package response.

consumed or used asset
  A manifest asset that the consumer actually inserted, embedded, rendered,
  attached, imported, copied into the output, or otherwise used.

fallback event
  A returned report event stating that the consumer could not use the expected
  file-backed approved ref for a slot.

blocking fallback reason
  A canonical reason that proves the fallback was caused by an actual blocking
  condition, not a generic consumer choice.
```

When a use slot declares an `approved_asset_ref` and that ref resolves to a
file-backed manifest asset, the consumer must do one of two things:

```text
1. Use the approved file and report same-slot evidence.
2. Report a canonical blocking fallback reason for that same slot and mark the
   returned status as fail or blocked.
```

Metadata-only candidates, policy-gated references, and package proposals do not
grant file use. File use begins only when an approved package response contains
a manifest asset for the declared ref.

## Evidence Contract

Returned reports may use `inserted_assets[]`, `events[]`, or both. The field
name `inserted_assets[]` is historical; for non-presentation consumers it means
the approved asset was consumed, used, rendered, embedded, attached, imported,
or otherwise applied in the output.

For each file-backed approved ref, valid evidence must show one of:

```text
inserted_assets[] evidence
  An inserted_assets[] entry names the same slot_id and relative_package_path,
  uses source_type=approved_package_file, sets file_backed=true, and reports
  matching checksum and size state.

same-slot events[] evidence
  An events[] entry names the same slot_id and package ref, uses
  source_type=approved_package_file, sets file_backed=true, sets
  fallback_used=false, and does not report failed checksum or size evidence.

blocking fallback evidence
  events[], fallbacks[], or fallback_events[] names the same slot_id and one of
  the canonical blocking fallback reasons, while the returned final QA or
  used-assets report status is fail or blocked.
```

Event-first consumers are compatible. A consumer does not have to duplicate
every event in `inserted_assets[]` when `events[]` already carries same-slot
approved-package evidence.

Path-only evidence is not sufficient by itself. An `inserted_assets[]` entry
that only reports a package path, without `slot_id` and without same-slot
`events[]` evidence, does not prove which declared use slot consumed the
approved ref.

Fallback-only pass or warn reports are invalid when a file-backed approved ref
exists for that slot. If the package provides a file-backed approved ref for a
slot, the consumer must either report consumption evidence or report a
canonical blocking fallback with fail or blocked status.

## Canonical Blocking Fallback Reasons

Use only these reason codes when a file-backed approved ref cannot be used:

```text
asset_file_missing
checksum_mismatch
file_size_mismatch
unsupported_media_type
policy_blocked
license_blocked
asset_unreadable
approved_asset_ref_not_in_manifest
```

Generic messages such as `no valid approved package asset` are not acceptable
when the approved package manifest contains the declared ref. The report should
say what blocked use of the specific slot and approved asset.

## Required Local Package Copy

Each consumer output root should keep the exact
`approved-package-response.json` used to build, render, or otherwise create that
output.

Returned-report validators should use this local copy where possible:

```text
output-root/
  approved-package-response.json
  final-qa-report.json
  used-assets-report.json
  rendered-output-or-build-artifacts/
```

This avoids validating a report against a different package response after a
later approval, regenerated package, or fixture update. The local copy must
remain public-safe and must contain only relative package refs, checksums, file
sizes, policy/license notes, and other approved public fields.

## JSON Examples

### Good inserted_assets[] consumption

```json
{
  "status": "pass",
  "inserted_assets": [
    {
      "slot_id": "hero_product_image",
      "approved_asset_ref": "assets/images/hero-product.png",
      "relative_package_path": "assets/images/hero-product.png",
      "source_type": "approved_package_file",
      "file_backed": true,
      "sha256": "sha256:1111111111111111111111111111111111111111111111111111111111111111",
      "checksum_valid": true,
      "size_bytes": 184212,
      "file_size_valid": true,
      "used_in_output": true
    }
  ],
  "events": []
}
```

### Good event-first events[] consumption

```json
{
  "status": "pass",
  "inserted_assets": [],
  "events": [
    {
      "event_type": "approved_asset_consumed",
      "slot_id": "supporting_icon",
      "approved_asset_ref": "assets/icons/supporting-icon.svg",
      "relative_package_path": "assets/icons/supporting-icon.svg",
      "source_type": "approved_package_file",
      "file_backed": true,
      "fallback_used": false,
      "checksum_valid": true,
      "file_size_valid": true
    }
  ]
}
```

### Good blocking fallback with fail/blocked status

```json
{
  "status": "blocked",
  "inserted_assets": [],
  "events": [
    {
      "event_type": "approved_asset_fallback",
      "slot_id": "background_visual",
      "approved_asset_ref": "assets/images/background-visual.webp",
      "relative_package_path": "assets/images/background-visual.webp",
      "fallback_used": true,
      "blocking_fallback_reason": "unsupported_media_type",
      "details": "The consumer cannot render this media type in the target output."
    }
  ]
}
```

### Bad generic fallback

```json
{
  "status": "warn",
  "events": [
    {
      "event_type": "approved_asset_fallback",
      "slot_id": "hero_product_image",
      "approved_asset_ref": "assets/images/hero-product.png",
      "fallback_used": true,
      "reason": "no valid approved package asset"
    }
  ]
}
```

This is invalid when the manifest contains `assets/images/hero-product.png`:
the reason is generic, the report is not fail or blocked, and the consumer did
not name a canonical blocking fallback reason.

### Bad path-only inserted asset evidence

```json
{
  "status": "pass",
  "inserted_assets": [
    {
      "relative_package_path": "assets/images/hero-product.png",
      "source_type": "approved_package_file",
      "file_backed": true,
      "checksum_valid": true,
      "file_size_valid": true
    }
  ],
  "events": []
}
```

This is invalid for a file-backed approved slot because it does not include the
declared `slot_id`, and no same-slot event proves consumption.

## Validator And Sendability Checklist

Before sending a request, response, package, or returned report across the
public/private boundary, verify:

```text
package manifest refs are relative and public-safe
approved package files match manifest checksum and size values
no private fields, private paths, Drive IDs, Drive links, tokens, or secrets
no raw private registry rows, generated private reports, or raw unapproved assets
file-backed approved refs are consumed or have canonical blocking fallback reports
returned final QA and used-assets report agree about used assets and blockers
path-only inserted asset evidence is paired with same-slot event evidence, or rejected
fallback-only pass/warn is rejected when a file-backed approved ref exists
prompt literal leakage is absent from rendered or user-facing output
known warnings are classified separately from blockers
```

Run the public toolkit checks from the repository root:

```powershell
git diff --check
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
.\tools\candidate-gate.ps1 -Operation leak-scan -Path .
.\tools\connector-client.ps1 -Operation validate-fixtures
```

If validation fails, treat the artifact as not sendable. Debug or unsafe-review
artifacts may be written only when the command and filename clearly mark them
non-sendable.
