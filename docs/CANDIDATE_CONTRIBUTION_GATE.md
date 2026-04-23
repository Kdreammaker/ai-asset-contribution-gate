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
downloaded-assets/candidates/pending/
downloaded-assets/candidates/preflight-failed/
downloaded-assets/candidates/review-required/
downloaded-assets/candidates/license-review-required/
downloaded-assets/candidates/approved/
downloaded-assets/candidates/rejected/
downloaded-assets/candidates/promoted/
downloaded-assets/candidates/superseded/
```

Candidate records follow:

```text
downloaded-assets/registry/candidate-record.schema.json
```

## Commands

Use `assetctl.ps1` from the workspace root.

Add a file as a candidate:

```powershell
.\downloaded-assets\tools\assetctl.ps1 candidate-add `
  -CandidatePath ".\downloaded-assets\_inbox\icons\example.svg" `
  -SourceUrl "https://example.invalid/source" `
  -SourceName "Tabler Icons" `
  -DeclaredLicense "MIT" `
  -DeclaredCommercialUseAllowed true `
  -AssetType icon `
  -IntendedUse ui
```

Review one candidate or all candidates:

```powershell
.\downloaded-assets\tools\assetctl.ps1 candidate-review -InputPath ".\downloaded-assets\candidates\review-required\cand-example.candidate.json"
.\downloaded-assets\tools\assetctl.ps1 candidate-review
```

Run a promotion dry-run:

```powershell
.\downloaded-assets\tools\assetctl.ps1 candidate-promote `
  -InputPath ".\downloaded-assets\candidates\approved\cand-example.candidate.json" `
  -ActorRole master `
  -Approve
```

Promotion output remains a dry-run report. Active registry activation stays
private, explicit, and approval-gated.

Validate the safety fixtures:

```powershell
.\downloaded-assets\tools\assetctl.ps1 candidate-validate-fixtures
```

Scan public-safe staging content before publishing:

```powershell
.\downloaded-assets\tools\assetctl.ps1 public-leak-scan -ScanPath ".\public-toolkit-staging"
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
downloaded-assets/registry/reports/candidate-preflight-report.json
downloaded-assets/registry/reports/candidate-license-review-report.json
downloaded-assets/registry/reports/candidate-duplicate-report.json
downloaded-assets/registry/reports/candidate-promotion-dry-run-report.json
downloaded-assets/registry/reports/candidate-fixture-validation-report.json
```

Do not commit generated report payloads unless the owner explicitly approves a
small documentation excerpt.

## Public Toolkit Boundary

The candidate gate engine, wrapper, schema, docs, and synthetic fixtures are
public-safe candidates after redaction validation. The public toolkit must not
include real candidate records, raw candidate files, generated reports, Drive
linkage, approval records, worklogs, local paths, or private source review
state.
