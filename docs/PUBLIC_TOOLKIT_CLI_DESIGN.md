# Public Toolkit CLI Design

## Purpose

This design defines the future public `assetctl` command surface for a reusable
asset-management toolkit. The CLI must operate against a private workspace that
pins the toolkit version. Normal commands must be offline-capable and must not
fetch the public repository during routine execution.

## Invocation Model

```text
assetctl <command> [options]
```

Every command should return a stable JSON envelope when `--json` is supplied:

```text
ok
operation_type
started_at
finished_at
inputs
outputs
warnings
errors
files_read
files_written
validation_summary
next_recommended_action
```

Human-readable output can be layered on top, but the JSON contract should remain
the AI-facing integration surface.

## Workspace Discovery

Command discovery order:

```text
1. Explicit --workspace path.
2. Current directory or ancestor containing .asset-workspace.json.
3. Current directory or ancestor containing downloaded-assets/registry.
4. Fail with a doctor suggestion.
```

The CLI should not infer private paths from machine-specific defaults. It should
read `.asset-workspace.json` and `.toolkit-version`.

## Commands

### `assetctl init`

Creates a new private workspace skeleton or validates an empty target.

Default behavior:

```text
create .asset-workspace.json from a template
create .toolkit-version
create candidate and report directories
create synthetic sample registry only when --with-sample-fixtures is supplied
do not download real assets
do not connect Drive or Slack
```

Risk level: low for skeleton creation, medium if overwriting an existing config.

### `assetctl link`

Links an existing private workspace to an installed toolkit.

Checks:

```text
workspace config exists
toolkit version is pinned
registry root is readable
policy paths are readable
connector readiness files are present only when enabled
```

It must not copy private registry state into the toolkit install location.

Current public toolkit bridge:

```powershell
.\tools\bootstrap-workspace.ps1
.\tools\assetctl-doctor.ps1
.\tools\setup-private-connector.ps1 -PrivateWorkspaceRoot "<owner-approved-private-workspace>" -CheckUpdates
```

The bridge writes only ignored local connector config and validates that the
private workspace exposes the connector runtime. It is the default setup path
for local maintainers that install the public repo and then need real private
asset search or approval-gated materialization. It must not auto-clone the
private repo or guess private paths by default. External-safe attachment uses
owner-provided proxy metadata or a scoped access-key identifier without storing
access-key secrets in the public repo.

### `assetctl doctor`

Diagnoses local readiness.

Default offline checks:

```text
toolkit version matches .toolkit-version
workspace config parses
schema versions are compatible
registry/policy paths exist
generated indexes are present or clearly marked missing
PowerShell/Python runtime availability is sufficient
connector readiness is reported without exposing secrets
```

Optional network checks:

```text
assetctl doctor --check-updates
assetctl doctor --check-connectors
```

No remote fetch should happen unless an explicit network flag is supplied.

### `assetctl validate`

Runs validation gates.

Modes:

```text
assetctl validate
assetctl validate --full
assetctl validate --scope system
assetctl validate --scope registry
assetctl validate --scope candidates
```

Default validation should be CI-compatible and fast. Full validation may stream
large registry exports or recalculate hashes.

### `assetctl quality`

Runs review-safe quality reports.

Modes:

```text
assetctl quality --asset-type palette
assetctl quality --asset-type icon
assetctl quality --asset-type font
assetctl quality --asset-type illustration
assetctl quality --asset-type image
assetctl quality --asset-type deck_component
assetctl quality --asset-type audio
assetctl quality --candidate-only
```

Quality commands report duplicates, near duplicates, weak labels, missing
metadata, and policy tensions. They must not delete, retire, promote, or
auto-approve assets.

### `assetctl candidate add`

Creates or imports a candidate record.

Inputs:

```text
--file
--asset-type
--source-url
--source-name
--declared-license
--commercial-use
--notes
--metadata
```

Behavior:

```text
hash file
read optional sidecar metadata
infer asset type when omitted
write candidate record
run local preflight
set status to review_required unless blocked as duplicate or unsafe
never write active registry records
```

Unknown source/license, paid license, commercial restriction, unclear user
source, and brand/trademark candidates must never auto-approve.

### `assetctl candidate review`

Runs non-mutating review over candidates.

Checks:

```text
schema completeness
source policy lookup
license policy lookup
commercial-use declaration
duplicate SHA lookup
near-duplicate check when a quality profile exists
brand/trademark keyword scan
prohibited usage scan
metadata completeness
```

Outputs:

```text
candidate preflight report
license review report
duplicate report
review queue summary
```

### `assetctl candidate promote`

Creates a promotion dry-run or applies an approved promotion.

Default:

```text
dry-run only
write proposal report
require explicit approval state
require maintainer/admin authority
```

Real promotion requires:

```text
approval.status = approved
no unresolved high-risk source/license findings
duplicate checks reviewed
rollback or backup path recorded
validation gates passed
```

The public toolkit can implement the proposal mechanics. The private workspace
owns approval records and active registry mutation.

### `assetctl registry rebuild`

Rebuilds generated private registry artifacts from private workspace inputs.

Behavior:

```text
read private manifest/source records
write generated registry/index/shard/preview outputs to private workspace
preserve history for missing/deleted assets
do not write public toolkit files
```

Generated outputs remain private and ignored unless the private workspace
explicitly tracks a lightweight source record.

### `assetctl graph build`

Builds the metadata graph from registry metadata.

Modes:

```text
assetctl graph build --scope catalog-sources
assetctl graph build --scope recommended
assetctl graph build --scope all-active
assetctl graph build --asset-type icon
assetctl graph build --type-partitions
```

This replaces whole-workspace graph updates for asset-library work. A future
`--graphify-update` flag should target only generated code-input shims.

### `assetctl search`

Searches private workspace indexes.

Inputs:

```text
--query
--query-file
--query-base64-utf8
--asset-type
--risk-level
--source-name
--include-brand-assets
--include-uxwing
--limit
```

Search should prefer generated lightweight indexes and fall back gracefully when
they are absent.

### `assetctl recommend`

Returns curated starting sets and policy notes.

Inputs:

```text
--use-case
--asset-type
--risk-level
--limit
```

Recommendations must include enough policy context for audit:

```text
asset_name
source_name
asset_type
risk_level
license_class
license_action
local_path or storage reference
notes_for_ai
```

## Offline And Update Policy

Offline by default:

```text
init
link
doctor
validate
quality
candidate add
candidate review
candidate promote --dry-run
registry rebuild
graph build
search
recommend
```

Network only when explicit:

```text
doctor --check-updates
self update
connector-specific read/write commands
package installation
remote CI workflows
```

## Private Data Handling

The CLI must keep these out of public toolkit directories:

```text
registry exports
raw assets
candidate files
Drive linkage
generated reports
lifecycle logs
approval records
worklogs
connector evidence
local absolute paths
```

It should write private outputs under paths configured by `.asset-workspace.json`.

## Compatibility Strategy

Each command should validate:

```text
workspace schema version
toolkit version
registry schema version
quality profile version
operation proposal schema version
```

Incompatible commands should fail closed with a clear `doctor` recommendation.
Mutation-capable commands should also require current validation to pass.
