# Candidate Contribution And License Safety Gate

## Purpose

B31-B adds a proposal-first candidate gate for user contributions. The gate lets
users submit assets, metadata fixes, tag translations, quality rules,
recommended-set changes, documentation changes, and source-policy suggestions
without directly mutating active registry records, protected policy files,
connector state, generated reports, or Drive storage.

The implementation is intentionally non-mutating with respect to active assets.
It writes candidate records and ignored review reports only.

## Candidate Lifecycle

```text
submitted
preflight_failed
review_required
license_review_required
approved
rejected
promoted
superseded
```

Storage directories:

```text
candidates/pending/
candidates/preflight-failed/
candidates/review-required/
candidates/license-review-required/
candidates/approved/
candidates/rejected/
candidates/promoted/
candidates/superseded/
```

Candidate records follow:

```text
schemas/candidate-record.schema.json
```

## Commands

Use `tools/candidate-gate.ps1` from the public toolkit root. A private
workspace can wrap the same engine with its own `assetctl.ps1` command router.

Add a file as a candidate:

```powershell
.\tools\candidate-gate.ps1 -Operation add `
  -File ".\sample-assets\example.svg" `
  -SourceUrl "https://example.invalid/source" `
  -SourceName "Tabler Icons" `
  -DeclaredLicense "MIT" `
  -DeclaredCommercialUseAllowed true `
  -AssetType icon `
  -IntendedUse ui
```

Review one candidate or all candidates:

```powershell
.\tools\candidate-gate.ps1 -Operation review -InputPath ".\candidates\review-required\cand-example.candidate.json"
.\tools\candidate-gate.ps1 -Operation review
```

Run a promotion dry-run:

```powershell
.\tools\candidate-gate.ps1 -Operation promote `
  -InputPath ".\candidates\approved\cand-example.candidate.json" `
  -ActorRole master `
  -Approve
```

Promotion output remains a dry-run report. Active registry activation stays
private, explicit, and approval-gated.

Validate the safety fixtures:

```powershell
.\tools\candidate-gate.ps1 -Operation validate-fixtures -AssetsRoot .
```

Scan public-safe staging content before publishing:

```powershell
.\tools\candidate-gate.ps1 -Operation leak-scan -Path .
```

## Preflight Checks

The gate checks:

```text
source URL presence
declared license
commercial-use declaration
file hash
allowed format
duplicate SHA
known source policy
license policy
brand/trademark keywords
paid marketplace/source terms
prohibited usage terms
metadata completeness
```

Automatic outcomes:

```text
safe_open_source_candidate -> review_required
unknown_license_candidate -> license_review_required
commercially_restricted_candidate -> license_review_required
paid_license_candidate -> license_review_required
brand_or_trademark_candidate -> license_review_required
duplicate_sha_candidate -> rejected
malformed_candidate -> preflight_failed
```

Never auto-approve:

```text
unknown license
unclear source
paid asset
commercial-use restricted asset
brand/trademark asset
user-uploaded file without source URL
AI-generated asset without generation/source/license metadata
```

## Reports

Generated reports stay under ignored local report paths:

```text
registry/reports/candidate-preflight-report.json
registry/reports/candidate-license-review-report.json
registry/reports/candidate-duplicate-report.json
registry/reports/candidate-promotion-dry-run-report.json
registry/reports/candidate-fixture-validation-report.json
```

Do not commit generated report payloads unless the owner explicitly approves a
small documentation excerpt.

## Public Toolkit Boundary

The candidate gate engine, wrapper, schema, docs, and synthetic fixtures are
public-safe candidates after redaction validation. The public toolkit must not
include real candidate records, raw candidate files, generated reports, Drive
linkage, approval records, worklogs, local paths, or private source review
state.
